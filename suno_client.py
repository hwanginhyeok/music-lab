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


class SunoError(Exception):
    """Suno 관련 에러."""


def _send_telegram(text: str) -> bool:
    """텔레그램 알림 전송."""
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.warning("텔레그램 알림 설정 없음 (ADMIN_CHAT_ID 필요)")
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


# 검증된 React 호환 입력 JS (input + change 이벤트 둘 다 디스패치)
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
        """실제 차단 캡차 감지 (페이지 임베드 스크립트는 무시)."""
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

            return False
        except Exception:
            return False

    def _wait_captcha(self) -> bool:
        """캡차 감지 시 알림 후 해결 대기."""
        if not self._detect_captcha():
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

    def generate(self, lyrics: str, style: str, title: str = "") -> list[str]:
        """곡 생성 → song URL 리스트 반환 (Suno는 2곡 동시 생성)."""
        driver = self._get_driver()
        logger.info("Suno 곡 생성 시작: %s", title or "무제")

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

        # Advanced 모드 활성화
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

        # JS로 가사 + 스타일 + 제목 입력
        try:
            result = driver.execute_script(JS_SET_VALUE, lyrics, style, title or "")
            logger.info("입력 완료: %s", result)
            if not result.get("createEnabled"):
                raise SunoError("Create 버튼 비활성화 — 입력이 반영되지 않음")
        except SunoError:
            raise
        except Exception as e:
            raise SunoError(f"입력 실패: {e}") from e

        time.sleep(1)

        # API로 기존 곡 ID 수집
        api = self._get_api()
        existing_ids = {s["id"] for s in api.get_songs(page=0) if s.get("id")}
        logger.info("기존 곡 %d개", len(existing_ids))

        # Create 버튼 클릭 (selenium element.click — 검증됨)
        try:
            for b in driver.find_elements(By.TAG_NAME, "button"):
                if b.is_displayed() and b.text.strip() == "Create" and b.is_enabled():
                    b.click()
                    logger.info("Create 버튼 클릭")
                    break
            else:
                raise SunoError("Create 버튼을 찾을 수 없습니다")
        except SunoError:
            raise
        except Exception as e:
            raise SunoError(f"Create 클릭 실패: {e}") from e

        time.sleep(3)
        if not self._wait_captcha():
            raise SunoError("Create 후 캡차 해결 실패")

        # API 폴링으로 생성 완료 대기 (최대 5분)
        logger.info("곡 생성 대기 중... (API 폴링)")
        _send_telegram(f"🎵 Suno 곡 생성 시작: {title or '무제'}\n대기 중...")

        new_songs = []
        for i in range(60):
            time.sleep(5)
            try:
                api._jwt = None  # JWT 갱신 강제
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
                elif i % 6 == 0:
                    logger.info("대기 중... (%d초)", i * 5)
            except Exception as e:
                logger.warning("API 폴링 실패: %s", e)

        if not new_songs:
            _send_telegram("❌ Suno 곡 생성 타임아웃 (5분)")
            raise SunoError("곡 생성 타임아웃 (5분)")

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
