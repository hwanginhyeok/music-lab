"""
Suno AI 클라이언트 — undetected-chromedriver 기반 웹 자동화

Cloudflare Turnstile 우회. 쿠키 인증으로 로그인 유지.
곡 생성 → 완료 대기 → 다운로드.
"""
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("music-lab")

SUNO_DIR = Path("data/suno")


class SunoError(Exception):
    """Suno 관련 에러."""


class SunoClient:
    """undetected-chromedriver 기반 Suno 자동화 클라이언트."""

    def __init__(self, cookie: str | None = None):
        self.cookie = cookie or os.getenv("SUNO_COOKIE", "")
        if not self.cookie:
            raise SunoError("SUNO_COOKIE 환경변수가 설정되지 않았습니다")
        self._driver = None

    def _get_driver(self):
        """undetected-chromedriver lazy init."""
        if self._driver is None:
            import undetected_chromedriver as uc

            options = uc.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")

            self._driver = uc.Chrome(options=options, version_main=146)

            # suno.com 접속 후 쿠키 주입
            self._driver.get("https://suno.com")
            time.sleep(3)
            for pair in self.cookie.split("; "):
                if "=" in pair:
                    name, val = pair.split("=", 1)
                    try:
                        self._driver.add_cookie({
                            "name": name.strip(),
                            "value": val.strip(),
                            "domain": ".suno.com",
                        })
                    except Exception:
                        pass
            logger.info("Suno 브라우저 초기화 완료")
        return self._driver

    def get_credits(self) -> int:
        """남은 크레딧 확인."""
        driver = self._get_driver()
        driver.get("https://suno.com/create")
        time.sleep(5)
        source = driver.page_source.lower()
        matches = re.findall(r"(\d+)\s*credit", source)
        return int(matches[0]) if matches else -1

    def generate(self, lyrics: str, style: str, title: str = "") -> list[str]:
        """곡 생성. song URL 리스트 반환 (Suno는 2곡 동시 생성)."""
        driver = self._get_driver()
        logger.info("Suno 곡 생성 시작: %s", title or "무제")

        # Create 페이지 접속
        driver.get("https://suno.com/create")
        time.sleep(5)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        wait = WebDriverWait(driver, 15)

        # 쿠키 배너 닫기
        try:
            accept_btn = driver.find_element(By.XPATH, "//button[contains(., 'Accept All')]")
            accept_btn.click()
            time.sleep(1)
        except Exception:
            pass

        # Advanced 모드 활성화 (Simple → Advanced)
        try:
            adv_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Advanced')]"))
            )
            adv_btn.click()
            time.sleep(2)
            logger.info("Advanced 모드 활성화")
        except Exception:
            logger.info("Advanced 버튼 못 찾음 — 이미 Advanced 모드일 수 있음")

        from selenium.webdriver.common.by import By
        # (re-import for clarity)

        # React 호환 값 설정 JS (proto.set 방식 — 검증됨)
        JS_SET_VALUE = '''
function setReactValue(element, value) {
    var valueSetter = Object.getOwnPropertyDescriptor(
        element.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype,
        "value"
    ).set;
    var protoSetter = Object.getOwnPropertyDescriptor(
        Object.getPrototypeOf(element), "value"
    );
    if (protoSetter && protoSetter.set && valueSetter !== protoSetter.set) {
        protoSetter.set.call(element, value);
    } else {
        valueSetter.call(element, value);
    }
    element.dispatchEvent(new Event("input", { bubbles: true }));
}

var lyrics = document.querySelector("textarea[placeholder*='Write some lyrics']");
if (lyrics) { lyrics.focus(); setReactValue(lyrics, arguments[0]); }

var textareas = document.querySelectorAll("textarea");
var styleTA = null;
for (var i = 0; i < textareas.length; i++) {
    if (textareas[i].offsetParent !== null &&
        !textareas[i].placeholder.includes("Write some lyrics")) {
        styleTA = textareas[i]; break;
    }
}
if (styleTA) { styleTA.focus(); setReactValue(styleTA, arguments[1]); }

var titleInput = document.querySelector("input[placeholder='Song Title (Optional)']");
if (titleInput) { titleInput.focus(); setReactValue(titleInput, arguments[2]); }

return {
    lyrics: lyrics ? lyrics.value.substring(0, 30) : "X",
    style: styleTA ? styleTA.value.substring(0, 30) : "X"
};
'''

        # 가사 + 스타일 + 제목 한번에 입력
        try:
            result = driver.execute_script(JS_SET_VALUE, lyrics, style, title or "")
            logger.info("입력 완료: %s", result)
            if not result.get("lyrics"):
                raise SunoError("가사 입력란을 찾을 수 없습니다")
            if not result.get("style"):
                raise SunoError("스타일 입력란을 찾을 수 없습니다")
        except SunoError:
            raise
        except Exception as e:
            raise SunoError(f"입력 실패: {e}") from e

        time.sleep(2)

        # 기존 곡 URL 수집 (Create 클릭 전에 — 새 곡 필터링용)
        source_before = driver.page_source
        existing_urls = set(re.findall(r'href="(/song/[a-f0-9-]+)"', source_before))

        # Create 버튼 클릭
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            create_btn = None
            for b in buttons:
                if b.is_displayed() and b.text.strip() == "Create":
                    create_btn = b
                    break
            if not create_btn:
                raise SunoError("Create 버튼을 찾을 수 없습니다")
            if create_btn.get_attribute("disabled"):
                raise SunoError("Create 버튼이 비활성화 상태입니다 (입력이 반영 안 됨)")
            create_btn.click()
            logger.info("Create 버튼 클릭")
        except SunoError:
            raise
        except Exception as e:
            raise SunoError(f"Create 버튼 클릭 실패: {e}") from e

        # 생성 완료 대기 (최대 5분)
        logger.info("곡 생성 대기 중...")
        new_urls = []
        for i in range(60):  # 60 * 5초 = 5분
            time.sleep(5)
            source = driver.page_source

            all_urls = set(re.findall(r'href="(/song/[a-f0-9-]+)"', source))
            new_urls = list(all_urls - existing_urls)

            if len(new_urls) >= 2:
                logger.info("곡 생성 완료: %d곡", len(new_urls))
                break

            if i % 6 == 0:
                logger.info("생성 중... (%d초)", i * 5)

        if not new_urls:
            raise SunoError("곡 생성 타임아웃 (5분)")

        return [f"https://suno.com{url}" for url in new_urls]

    def download(self, song_url: str, output_path: str | None = None) -> Path:
        """곡 페이지에서 오디오 URL 추출 후 다운로드."""
        driver = self._get_driver()
        driver.get(song_url)
        time.sleep(5)

        source = driver.page_source

        # audio URL 추출 (mp3/wav) — 이스케이프 문자 제거
        audio_matches = re.findall(
            r'(https://cdn[^"\'\\]+\.(?:mp3|wav|m4a))', source
        )
        if not audio_matches:
            raise SunoError(f"오디오 URL을 찾을 수 없습니다: {song_url}")

        audio_url = audio_matches[0]
        SUNO_DIR.mkdir(parents=True, exist_ok=True)

        if output_path:
            path = Path(output_path)
        else:
            # URL에서 song_id 추출
            song_id = song_url.rstrip("/").split("/")[-1]
            ext = "mp3" if ".mp3" in audio_url else "wav"
            path = SUNO_DIR / f"{song_id}.{ext}"

        import requests
        resp = requests.get(audio_url, timeout=60)
        resp.raise_for_status()

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
        logger.info("다운로드 완료: %s (%.1fMB)", path, len(resp.content) / 1024 / 1024)
        return path

    def close(self):
        """브라우저 종료."""
        if self._driver:
            self._driver.quit()
            self._driver = None
