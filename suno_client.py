"""
Suno AI 클라이언트 — VNC 디스플레이 + Chrome 자동화

Chrome을 remote-debugging 모드로 VNC 가상 디스플레이(:1)에서 실행.
전용 프로필(chrome-suno)로 Suno 로그인 유지.
캡차 감지 시 텔레그램 알림 → noVNC에서 수동 풀기 → 자동 재개.
곡 생성 완료 감지는 Clerk JWT API 폴링 (페이지 소스 파싱보다 안정적).
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("music-lab")

SUNO_DIR = Path("data/suno")
VNC_DISPLAY = os.getenv("VNC_DISPLAY", ":1")
CHROME_PROFILE = os.path.expanduser(
    os.getenv("CHROME_PROFILE", "~/.config/chrome-suno")
)
CHROME_DEBUG_PORT = int(os.getenv("CHROME_DEBUG_PORT", "9222"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
CAPTCHA_TIMEOUT = 300
POLL_TIMEOUT = int(os.getenv('SUNO_POLL_TIMEOUT', '300'))
POLL_INTERVAL = 5
POLL_ITERATIONS = max(1, POLL_TIMEOUT // POLL_INTERVAL)


class SunoError(Exception):
    """Suno 관련 에러."""


def _send_telegram(text: str) -> bool:
    """텔레그램 알림 전송."""
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.warning("텔레그램 알림 설정 없음 (ADMIN_CHAT_ID 필요)")
        # 캡차 메시지면 콘솔에도 명확히 표시
        if "캡차" in text or "captcha" in text.lower():
            print(f"\n{'='*60}\n[USER ACTION REQUIRED]\n{text}\n{'='*60}\n", flush=True)
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": text},
            timeout=10,
        )
        return resp.ok
    except Exception as e:
        logger.warning("텔레그램 알림 실패: %s", e)
        return False


def _chrome_running(port: int = CHROME_DEBUG_PORT) -> bool:
    """Chrome remote debugging 포트 응답 확인."""
    try:
        r = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
        return r.ok
    except Exception:
        return False


def _start_chrome(display: str = VNC_DISPLAY, port: int = CHROME_DEBUG_PORT):
    """VNC 디스플레이에서 Chrome 시작 (remote debugging 모드)."""
    if os.getuid() == 0:
        logger.warning("Chrome을 root로 실행 중 — --no-sandbox 보안 위험. non-root 사용자 권장.")
    env = os.environ.copy()
    env["DISPLAY"] = display
    subprocess.Popen(
        [
            "google-chrome",
            f"--user-data-dir={CHROME_PROFILE}",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1280,720",
            "--no-first-run",
            "--no-default-browser-check",
            f"--remote-debugging-port={port}",
            "about:blank",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Chrome 시작 대기
    for _ in range(10):
        time.sleep(1)
        if _chrome_running(port):
            return
    raise SunoError("Chrome 시작 실패")


# 검증된 React 호환 입력 JS (input + change 이벤트 둘 다 디스패치) — 가사 포함 버전
JS_SET_VALUE = """
function setNativeValue(element, value) {
    var proto = element.tagName === 'TEXTAREA' ? HTMLTextAreaElement : HTMLInputElement;
    var valueSetter = Object.getOwnPropertyDescriptor(proto.prototype, 'value').set;
    var protoSetter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), 'value');
    if (protoSetter && protoSetter.set && valueSetter !== protoSetter.set) {
        protoSetter.set.call(element, value);
    } else {
        valueSetter.call(element, value);
    }
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
}

var textareas = document.querySelectorAll('textarea');
var results = {};

// textarea[0] = lyrics (placeholder에 'Write some lyrics' 포함)
if (textareas[0]) {
    textareas[0].focus();
    setNativeValue(textareas[0], arguments[0]);
    results.lyrics = textareas[0].value.substring(0, 30);
}

// textarea[1] = style of music
if (textareas[1] && textareas[1].offsetParent !== null) {
    textareas[1].focus();
    setNativeValue(textareas[1], arguments[1]);
    results.style = textareas[1].value.substring(0, 30);
}

// title input
var titleInput = document.querySelector("input[placeholder='Song Title (Optional)']");
if (titleInput) {
    titleInput.focus();
    setNativeValue(titleInput, arguments[2]);
    results.title = titleInput.value;
}

// Create 버튼 상태
var buttons = document.querySelectorAll('button');
for (var b of buttons) {
    if (b.textContent.trim() === 'Create') {
        results.createEnabled = !b.disabled;
    }
}

return results;
"""

# Advanced 모드 Instrumental 전용 JS — 빈 lyrics + style만 입력
JS_SET_VALUE_INSTRUMENTAL = """
function setNativeValue(element, value) {
    var proto = element.tagName === 'TEXTAREA' ? HTMLTextAreaElement : HTMLInputElement;
    var setter = Object.getOwnPropertyDescriptor(proto.prototype, 'value').set;
    setter.call(element, value);
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
}

var results = {};

// Lyrics textarea — 빈 문자열 명시 입력
var lyricsTa = document.querySelector('textarea[data-testid="lyrics-textarea"]');
if (lyricsTa) {
    lyricsTa.focus();
    setNativeValue(lyricsTa, '');
    lyricsTa.blur();
    results.lyrics = 'cleared(' + lyricsTa.value.length + ')';
} else {
    results.lyrics = 'lyrics-textarea-not-found';
}

// Style of Music — Advanced 모드의 두 번째 visible textarea (lyrics 아닌 것)
var styleTa = null;
document.querySelectorAll('textarea').forEach(function(t) {
    if (t.dataset.testid === 'lyrics-textarea') return;
    if (t.offsetParent === null) return;
    var s = window.getComputedStyle(t);
    if (s.visibility === 'hidden' || s.display === 'none') return;
    if (!styleTa) styleTa = t;
});
if (styleTa) {
    styleTa.focus();
    setNativeValue(styleTa, arguments[0]);
    results.style = styleTa.value.substring(0, 30);
} else {
    results.style = 'style-textarea-not-found';
}

// Title input
var titleInput = document.querySelector('input[placeholder="Song Title (Optional)"]');
if (titleInput) {
    titleInput.focus();
    setNativeValue(titleInput, arguments[1]);
    results.title = titleInput.value.substring(0, 30);
}

// Create 버튼 활성화 상태
var btns = document.querySelectorAll('button');
for (var b of btns) {
    if ((b.textContent || '').trim() === 'Create') {
        results.createEnabled = !b.disabled;
        results.createDisabledAttr = b.getAttribute('disabled');
        break;
    }
}

return results;
"""


class SunoClient:
    """Chrome + VNC + Clerk JWT API 기반 Suno 자동화 클라이언트.

    흐름: Chrome으로 UI 조작 (입력 + Create 클릭) → API로 생성 완료 감지 + 다운로드.
    """

    def __init__(self, display: str | None = None, keep_browser: bool = True):
        self.display = display or VNC_DISPLAY
        self.keep_browser = keep_browser
        self._driver = None

    def _get_driver(self):
        """Chrome에 attach. 실행 중이 아니면 자동 시작."""
        if self._driver is not None:
            return self._driver

        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        # Chrome이 안 떠있으면 시작
        if not _chrome_running():
            logger.info("Chrome 시작 중... (display=%s)", self.display)
            _start_chrome(self.display)

        # remote debugging으로 attach
        options = Options()
        options.debugger_address = f"127.0.0.1:{CHROME_DEBUG_PORT}"
        self._driver = webdriver.Chrome(options=options)
        logger.info("Chrome 연결 완료 (port=%d)", CHROME_DEBUG_PORT)
        return self._driver

    def _detect_captcha(self) -> bool:
        """실제 차단 캡차 감지 (iframe + Suno 이미지 선택 팝업 포함)."""
        driver = self._driver
        if not driver:
            return False
        try:
            from selenium.webdriver.common.by import By

            # 보이는 캡차 iframe
            for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
                src = (iframe.get_attribute("src") or "").lower()
                if not iframe.is_displayed():
                    continue
                size = iframe.size
                if size.get("height", 0) > 50 and size.get("width", 0) > 50:
                    if any(s in src for s in ["hcaptcha", "turnstile", "captcha"]):
                        return True

            # Cloudflare 차단 페이지
            title = driver.title.lower()
            if "just a moment" in title or "attention required" in title:
                return True

            # hCaptcha 오버레이
            for el in driver.find_elements(
                By.CSS_SELECTOR, "[class*='captcha'], [id*='captcha'], .h-captcha"
            ):
                if el.is_displayed() and el.size.get("height", 0) > 50:
                    return True

            # Suno 이미지 선택 캡차 팝업 감지 (건너뛰기/검사 버튼 있는 팝업)
            for btn in driver.find_elements(By.TAG_NAME, "button"):
                try:
                    txt = btn.text.strip()
                    if txt in ("건너뛰기", "검사", "Skip", "Verify") and btn.is_displayed():
                        return True
                except Exception:
                    continue

            return False
        except Exception:
            return False

    def _try_skip_captcha(self) -> bool:
        """Suno 이미지 캡차 '건너뛰기' 버튼 자동 클릭 시도."""
        driver = self._driver
        if not driver:
            return False
        try:
            from selenium.webdriver.common.by import By
            for btn in driver.find_elements(By.TAG_NAME, "button"):
                txt = btn.text.strip()
                if txt in ("건너뛰기", "Skip") and btn.is_displayed():
                    btn.click()
                    logger.info("캡차 '건너뛰기' 클릭")
                    time.sleep(2)
                    return True
        except Exception:
            pass
        return False

    def _wait_captcha(self) -> bool:
        """캡차 감지 시 건너뛰기 시도 → 실패 시 알림 후 해결 대기."""
        if not self._detect_captcha():
            return True

        # 먼저 건너뛰기 버튼 자동 클릭 시도
        if self._try_skip_captcha():
            time.sleep(2)
            if not self._detect_captcha():
                logger.info("캡차 건너뛰기 성공 — 자동 재개")
                return True

        logger.warning("캡차 감지! 사용자 개입 필요")
        _send_telegram(
            "🔐 Suno 캡차 감지!\n"
            "noVNC에서 풀어주세요.\n"
            "http://localhost:6080/vnc.html"
        )

        start = time.time()
        while time.time() - start < CAPTCHA_TIMEOUT:
            time.sleep(3)
            # 매 루프마다 건너뛰기 재시도
            self._try_skip_captcha()
            if not self._detect_captcha():
                logger.info("캡차 해결됨 — 자동 재개")
                _send_telegram("✅ 캡차 해결! 자동화 재개합니다.")
                time.sleep(2)
                return True
            elapsed = int(time.time() - start)
            if elapsed % 30 == 0:
                logger.info("캡차 대기 중... (%d초)", elapsed)

        logger.error("캡차 타임아웃 (%d초)", CAPTCHA_TIMEOUT)
        _send_telegram("❌ 캡차 타임아웃 — 자동화 중단됨")
        return False

    def _get_api(self):
        """suno_download.py의 SunoAPI 인스턴스."""
        if not hasattr(self, "_api"):
            from suno_download import SunoAPI
            self._api = SunoAPI()
        return self._api

    def get_credits(self) -> int:
        """남은 크레딧 (API)."""
        return self._get_api().get_credits()

    def _select_model(self, version: str) -> bool:
        """Advanced Mode 모델 드롭다운에서 버전 선택. 실패 시 스크린샷 + WARN + False 반환."""
        driver = self._driver
        if not driver or not version:
            return False

        from selenium.webdriver.common.by import By

        debug_dir = Path("data/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)

        try:
            # (a) 모델 드롭다운 버튼 후보 — 'v5', 'v4', 'Model', 'Chirp'
            dropdown = None
            selectors_open = [
                "//button[.//text()[contains(., 'v5')] or .//text()[contains(., 'v4')]]",
                "//button[contains(., 'Model') or contains(., 'Chirp')]",
                "//button[@aria-haspopup='listbox' or @aria-haspopup='menu']",
            ]
            for xp in selectors_open:
                try:
                    for el in driver.find_elements(By.XPATH, xp):
                        if el.is_displayed():
                            dropdown = el
                            break
                    if dropdown:
                        break
                except Exception:
                    continue

            if not dropdown:
                ts = int(time.time())
                driver.save_screenshot(
                    str(debug_dir / f"model_select_fail_dropdown_{ts}.png")
                )
                logger.warning(
                    "모델 드롭다운 못 찾음 — 기본 모델로 진행 (screenshot 저장)"
                )
                return False

            dropdown.click()
            time.sleep(1)

            # (b) 옵션 찾기 — v5.5 / v5 / v4.5 / v4 / v3.5
            target_texts = [version, version.replace("v", "V"), version.upper()]
            if version == "v5.5":
                target_texts += ["5.5", "Chirp v5.5", "Chirp 5.5"]

            option = None
            option_xpaths = [
                "//div[@role='option']",
                "//li[@role='option']",
                "//button[@role='menuitem']",
                "//div[@role='menuitem']",
                "//span[@role='option']",
            ]
            for xp in option_xpaths:
                try:
                    for el in driver.find_elements(By.XPATH, xp):
                        if not el.is_displayed():
                            continue
                        text = (el.text or "").strip()
                        if any(t in text for t in target_texts):
                            option = el
                            break
                    if option:
                        break
                except Exception:
                    continue

            if not option:
                ts = int(time.time())
                driver.save_screenshot(
                    str(debug_dir / f"model_select_fail_option_{ts}.png")
                )
                logger.warning(
                    "모델 옵션 %s 못 찾음 — 드롭다운은 열렸으나 옵션 매칭 실패 (screenshot 저장)",
                    version,
                )
                # 드롭다운 닫기
                try:
                    driver.execute_script("document.body.click();")
                except Exception:
                    pass
                return False

            option.click()
            time.sleep(1)
            logger.info("모델 선택 완료: %s", version)
            return True
        except Exception as e:
            ts = int(time.time())
            try:
                driver.save_screenshot(
                    str(debug_dir / f"model_select_fail_exc_{ts}.png")
                )
            except Exception:
                pass
            logger.warning("모델 선택 중 예외 — 기본 모델로 진행: %s", e)
            return False

    def _toggle_instrumental(self) -> bool:
        """Instrumental 토글 best-effort 클릭. 보이지 않으면 스킵 (placeholder 동작에 위임)."""
        from selenium.webdriver.common.by import By
        driver = self._driver
        if not driver:
            return True
        try:
            btn = driver.execute_script("""
            var b = document.querySelector('button[aria-label="Check this to generate an instrumental only song"]');
            if (!b) return null;
            var s = window.getComputedStyle(b);
            var ps = b.parentElement ? window.getComputedStyle(b.parentElement) : null;
            var visible = s.visibility !== 'hidden' && s.display !== 'none' && (!ps || ps.visibility !== 'hidden');
            if (visible) { b.click(); return 'clicked'; }
            return 'hidden';
            """)
            logger.info('Instrumental 토글 상태: %s', btn or 'not-found')
        except Exception as e:
            logger.warning('Instrumental 토글 처리 예외 (스킵): %s', e)
        return True

    def _switch_to_simple_instrumental(self) -> bool:
        """Simple 모드 전환 + Instrumental 탭 활성화. ActionChains 필수.

        A 시도 — 봇 감지로 4회 실패. 보존만 (롤백용).
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains
        driver = self._driver
        if not driver:
            return False
        try:
            # 1) Simple 버튼 (이미 active면 스킵)
            simple_btn = driver.find_element(By.XPATH, "//button[.//span[normalize-space()='Simple']]")
            if 'active' not in (simple_btn.get_attribute('class') or ''):
                ActionChains(driver).move_to_element(simple_btn).pause(0.3).click().perform()
                time.sleep(2)
                logger.info('Simple 모드 전환')
            else:
                logger.info('이미 Simple 모드')

            # 2) Instrumental 탭 클릭
            inst_btn = driver.find_element(
                By.XPATH,
                '//button[@aria-label="Check this to generate an instrumental only song"]'
            )
            ActionChains(driver).move_to_element(inst_btn).pause(0.3).click().perform()
            time.sleep(1.5)
            logger.info('Instrumental 탭 클릭')
            return True
        except Exception as e:
            ts = int(time.time())
            from pathlib import Path
            Path('data/debug').mkdir(parents=True, exist_ok=True)
            try:
                driver.save_screenshot(f'data/debug/simple_instrumental_fail_{ts}.png')
            except Exception:
                pass
            logger.error('Simple+Instrumental 시퀀스 실패: %s', e)
            return False

    def generate(
        self,
        lyrics: str,
        style: str,
        title: str = "",
        model: str = "v5.5",
        instrumental: bool = False,
    ) -> list[str]:
        """곡 생성 → song URL 리스트 반환 (Suno는 2곡 동시 생성).

        Args:
            lyrics: 가사 텍스트 (instrumental=True时 무시됨)
            style: Style of Music 태그
            title: 곡 제목 (선택)
            model: v3.5 / v4 / v4.5 / v5 / v5.5. 기본 v5.5. UI 선택 실패 시 기본 모델로 폴백.
            instrumental: 인스트루멘탈 모드 (가사 없이 곡 생성). 기본 False.

        Returns:
            생성된 곡 URL 리스트 (보통 2개)
        """
        driver = self._get_driver()
        logger.info("Suno 곡 생성 시작: %s (model=%s)", title or "무제", model)

        # 페이지 상태 초기화 — 다른 페이지 갔다가 Create로 복귀
        driver.get("https://suno.com/explore")
        time.sleep(3)
        driver.get("https://suno.com/create")
        time.sleep(5)

        if not self._wait_captcha():
            raise SunoError("캡차 해결 실패")

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        wait = WebDriverWait(driver, 15)

        # 쿠키 배너 닫기
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(., 'Accept All')]")
            btn.click()
            time.sleep(1)
        except Exception:
            pass

        # 인스트루멘탈 모드 처리
        if instrumental:
            # (A) Simple 모드 시도는 봇 감지로 4회 실패. 보존만.
            # if not self._switch_to_simple_instrumental():
            #     raise SunoError("Simple+Instrumental 전환 실패")

            # (C) Advanced 모드 + 빈 lyrics input event 경로
            logger.info('인스트루멘탈 모드 — Advanced + 빈 lyrics input event')
            # Advanced 모드 활성화 (이미 기본값일 가능성)
            try:
                adv = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(., 'Advanced')]")
                ))
                if 'active' not in (adv.get_attribute('class') or ''):
                    adv.click()
                    time.sleep(2)
                    logger.info('Advanced 모드 활성화')
                else:
                    logger.info('이미 Advanced 모드')
            except Exception:
                logger.info('Advanced 모드 토글 처리 스킵 (이미 진입했거나 셀렉터 변경)')
            # 모델 선택 (v5.5 기본)
            if model and model != 'v5.5':
                self._select_model(model)
            try:
                from selenium.webdriver.common.keys import Keys
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(0.5)
            except Exception:
                pass
        else:
            # 기존 Advanced 경로 (가사 있는 경우) 그대로 유지
            try:
                adv = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., 'Advanced')]")
                    )
                )
                adv.click()
                time.sleep(2)
                logger.info("Advanced 모드 활성화")
            except Exception:
                logger.info("이미 Advanced 모드")

            # 모델 선택 (UI 기본값 v5.5 — Pro 플랜). v5.5면 스킵, 다른 버전만 드롭다운 조작.
            # 드롭다운이 열린 채 남으면 Create 버튼을 덮어서 생성 요청 가로챔 — ESC로 강제 닫기 보장.
            if model and model != "v5.5":
                self._select_model(model)
            try:
                from selenium.webdriver.common.keys import Keys
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(0.5)
            except Exception:
                pass

        # send_keys 방식으로 입력 (React v5.5 호환)
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys as SeleniumKeys

            result = {'lyrics': '', 'style': '', 'title': '', 'createEnabled': False}

            all_tas = driver.find_elements(By.TAG_NAME, 'textarea')
            visible_tas = [t for t in all_tas if t.is_displayed()]

            # lyrics textarea: placeholder에 'lyrics' 포함하거나 첫 번째
            lyrics_ta = None
            style_ta = None
            for t in visible_tas:
                ph = (t.get_attribute('placeholder') or '').lower()
                if 'lyric' in ph or 'write some' in ph:
                    lyrics_ta = t
                else:
                    style_ta = t

            def _js_click_and_type(element, text):
                """JS click → ActionChains type (element not interactable 우회)."""
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});"
                    "arguments[0].focus();"
                    "arguments[0].click();",
                    element
                )
                time.sleep(0.5)
                ActionChains(driver).move_to_element(element).click().perform()
                time.sleep(0.3)
                ActionChains(driver).key_down(SeleniumKeys.CONTROL).send_keys('a').key_up(SeleniumKeys.CONTROL).perform()
                time.sleep(0.1)
                # 긴 텍스트는 청크로 나눠 입력
                chunk = 500
                for i in range(0, len(text), chunk):
                    ActionChains(driver).send_keys(text[i:i+chunk]).perform()
                    time.sleep(0.1)

            # lyrics 입력
            if lyrics_ta and not instrumental:
                _js_click_and_type(lyrics_ta, lyrics)
                val = lyrics_ta.get_attribute('value') or ''
                result['lyrics'] = val[:30] if val else lyrics[:30]

            # style 입력
            if not style_ta:
                style_ta = next((t for t in visible_tas if t != lyrics_ta), None)
            if style_ta:
                _js_click_and_type(style_ta, style)
                val = style_ta.get_attribute('value') or ''
                result['style'] = val[:30] if val else style[:30]

            # title 입력
            title_input = None
            for inp in driver.find_elements(By.TAG_NAME, 'input'):
                ph = (inp.get_attribute('placeholder') or '').lower()
                if 'title' in ph or 'song' in ph:
                    title_input = inp
                    break
            if title_input and title:
                _js_click_and_type(title_input, title or '')
                result['title'] = title or ''

            # Create 버튼 활성화 확인
            time.sleep(1)
            for b in driver.find_elements(By.TAG_NAME, 'button'):
                if b.text.strip() == 'Create':
                    result['createEnabled'] = not b.get_attribute('disabled')
                    break

            print(f'[입력 결과] {result}', flush=True)
            logger.info('입력 결과: %s', result)
            if not result.get('createEnabled'):
                ts = int(time.time())
                from pathlib import Path
                Path('data/debug').mkdir(parents=True, exist_ok=True)
                driver.save_screenshot(f'data/debug/create_disabled_{ts}.png')
                raise SunoError(f'Create 비활성 — 입력 미반영: {result}')
        except SunoError:
            raise
        except Exception as e:
            raise SunoError(f'입력 실패: {e}') from e

        time.sleep(1)

        # API로 기존 곡 ID 수집
        api = self._get_api()
        existing_ids = {s["id"] for s in api.get_songs(page=0) if s.get("id")}
        logger.info("기존 곡 %d개", len(existing_ids))

        # Create 버튼 클릭 (element.click 실패 시 JS click 폴백)
        create_btn = None
        for b in driver.find_elements(By.TAG_NAME, "button"):
            try:
                if not (b.is_displayed() and b.is_enabled()):
                    continue
                label = (b.get_attribute("aria-label") or "").lower()
                txt = (b.text or "").strip()
                if txt == "Create" or "create song" in label:
                    create_btn = b
                    break
            except Exception:
                continue

        if not create_btn:
            raise SunoError("Create 버튼을 찾을 수 없습니다")

        try:
            create_btn.click()
            logger.info("Create 버튼 클릭 (selenium)")
        except Exception as e1:
            logger.warning("element.click 실패 (%s) — JS click 폴백", type(e1).__name__)
            try:
                driver.execute_script("arguments[0].click();", create_btn)
                logger.info("Create 버튼 클릭 (JS)")
            except Exception as e2:
                raise SunoError(f"Create 클릭 실패: {e2}") from e2

        # 진단: Create 클릭 직후 5초간 변화 캡처
        ts0 = int(time.time())
        for k in range(5):
            time.sleep(1)
            try:
                driver.save_screenshot(f'data/debug/poc6_after_create_{ts0}_{k}.png')
                print(f'[Create+{k+1}s] url={driver.current_url} title={driver.title!r}', flush=True)
            except Exception:
                pass

        time.sleep(3)
        if not self._wait_captcha():
            raise SunoError("Create 후 캡차 해결 실패")

        # API 폴링으로 생성 완료 대기 (기본 5분, SUNO_POLL_TIMEOUT 환경변수로 조정 가능)
        logger.info("곡 생성 대기 중... (API 폴링)")
        _send_telegram(f"🎵 Suno 곡 생성 시작: {title or '무제'}\n대기 중...")

        new_songs = []
        captcha_handled_in_poll = False

        # 폴링 시작 직전에 크레딧 baseline
        try:
            initial_credits = api.get_credits()
            print(f'[폴링 시작] 크레딧 baseline: {initial_credits}', flush=True)
        except Exception:
            initial_credits = None

        for i in range(POLL_ITERATIONS):
            time.sleep(POLL_INTERVAL)
            # 12 cycles = 60초마다 크레딧 차감 점검
            if i > 0 and i % 12 == 0 and initial_credits is not None:
                try:
                    cur = api.get_credits()
                    if cur < initial_credits:
                        print(f'[폴링 {i*5}s] 크레딧 차감 감지: {initial_credits} → {cur}', flush=True)
                except Exception:
                    pass
            # 30초마다 캡차 재검사 (Create 후 지연 발생 가능)
            if i > 0 and i % 6 == 0 and not captcha_handled_in_poll:
                if self._detect_captcha():
                    logger.info("폴링 중 캡차 감지 — 해결 대기")
                    if self._wait_captcha():
                        captcha_handled_in_poll = True
            try:
                api.refresh_jwt()  # JWT 갱신 강제
                current = api.get_songs(page=0)
                new_complete = [
                    s for s in current
                    if s.get("id") and s["id"] not in existing_ids
                    and s.get("status") == "complete"
                ]

                if new_complete:
                    new_songs = new_complete
                    logger.info("곡 생성 완료: %d곡", len(new_songs))
                    _send_telegram(
                        f"✅ Suno 생성 완료! {len(new_songs)}곡\n"
                        + "\n".join(
                            f"https://suno.com/song/{s['id']}" for s in new_songs
                        )
                    )
                    break

                pending = [
                    s for s in current
                    if s.get("id") and s["id"] not in existing_ids
                    and s.get("status") != "complete"
                ]
                if pending:
                    logger.info(
                        "생성 중... (%d초, status=%s)",
                        i * 5, pending[0].get("status"),
                    )
                elif i % 12 == 0:
                    logger.info("대기 중... (%d초)", i * 5)
            except Exception as e:
                logger.warning("API 폴링 실패: %s", e)

        if not new_songs:
            _send_telegram(f"❌ Suno 곡 생성 타임아웃 ({POLL_TIMEOUT}초)")
            raise SunoError(f"곡 생성 타임아웃 ({POLL_TIMEOUT}초)")

        return [f"https://suno.com/song/{s['id']}" for s in new_songs]

    def download(self, song_url: str, output_path: str | None = None) -> Path:
        """API 기반 곡 다운로드."""
        song_id = song_url.rstrip("/").split("/")[-1]
        api = self._get_api()
        song = api.get_song(song_id)
        if not song:
            raise SunoError(f"곡 조회 실패: {song_id}")

        audio_url = song.get("audio_url")
        if not audio_url:
            raise SunoError(f"오디오 URL 없음: {song_id}")

        SUNO_DIR.mkdir(parents=True, exist_ok=True)
        if output_path:
            path = Path(output_path)
        else:
            ext = "mp3" if ".mp3" in audio_url else "wav"
            path = SUNO_DIR / f"{song_id}.{ext}"

        resp = requests.get(audio_url, timeout=60)
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
        logger.info("다운로드 완료: %s (%.1fMB)", path, len(resp.content) / 1024 / 1024)
        return path

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """selenium 연결 해제. keep_browser=True면 Chrome은 유지."""
        if self._driver:
            if self.keep_browser:
                # selenium detach만 (Chrome은 계속 실행)
                try:
                    self._driver.service.stop()
                except Exception:
                    pass
            else:
                self._driver.quit()
            self._driver = None
