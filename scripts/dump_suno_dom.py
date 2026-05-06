"""Suno Create 페이지 DOM 덤프 + 'Instrumental' 토글 후보 탐색.

이미 떠있는 chrome-suno (port 9222)에 attach. 페이지를 /create로 이동시키고
Advanced 모드 펼친 뒤 outerHTML 전체와 'instrumental' 매칭 후보를 추출.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

OUT_DIR = Path("songs/14_geuriumi/tracks/_tools")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR = Path("data/debug")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def attach_chrome():
    opts = Options()
    opts.debugger_address = "127.0.0.1:9222"
    return webdriver.Chrome(options=opts)


def main():
    driver = attach_chrome()
    print("[1] Chrome attached")

    driver.get("https://suno.com/create")
    time.sleep(5)
    print(f"[2] /create loaded — title: {driver.title!r}")

    # Advanced 모드 활성화 (이미 켜져 있으면 무시)
    try:
        for b in driver.find_elements(By.XPATH, "//button[contains(., 'Advanced')]"):
            if b.is_displayed():
                b.click()
                time.sleep(2)
                print("[3] Advanced 클릭")
                break
    except Exception as e:
        print(f"[3] Advanced 클릭 스킵: {e}")

    ts = int(time.time())
    driver.save_screenshot(str(DEBUG_DIR / f"dom_dump_before_more_{ts}.png"))

    # 1차 덤프
    html_before = driver.execute_script("return document.documentElement.outerHTML;")
    (OUT_DIR / "suno_dom_dump_before.html").write_text(html_before, encoding="utf-8")
    print(f"[4] before-dump 저장 ({len(html_before):,} chars)")

    # 'More Options' / 'Advanced Options' 펼치기 시도
    more_clicked = False
    for xp in [
        "//button[contains(., 'More Options')]",
        "//button[contains(., 'Advanced Options')]",
        "//div[contains(@class, 'more-options')]//button",
    ]:
        try:
            for el in driver.find_elements(By.XPATH, xp):
                if el.is_displayed():
                    el.click()
                    time.sleep(2)
                    more_clicked = True
                    print(f"[5] 펼침 성공: {xp}")
                    break
            if more_clicked:
                break
        except Exception as e:
            print(f"[5] {xp} 실패: {e}")

    if not more_clicked:
        print("[5] More Options 버튼 없음 — 이미 펼쳐졌거나 다른 위치")

    driver.save_screenshot(str(DEBUG_DIR / f"dom_dump_after_more_{ts}.png"))

    # 2차 덤프 (펼친 후)
    html_after = driver.execute_script("return document.documentElement.outerHTML;")
    (OUT_DIR / "suno_dom_dump_after.html").write_text(html_after, encoding="utf-8")
    print(f"[6] after-dump 저장 ({len(html_after):,} chars)")

    # 'instrumental' 키워드 후보 추출 (case-insensitive)
    candidates = []
    pattern = re.compile(
        r"<([a-z][a-z0-9]*)(\s+[^>]*?)?>([^<]*?instrumental[^<]*?)</\1>"
        r"|<[^>]*?(?:aria-label|data-testid|id|name|title|placeholder)\s*=\s*[\"'][^\"']*?instrumental[^\"']*?[\"'][^>]*?>"
        r"|<[^>]*?role\s*=\s*[\"'](?:switch|checkbox|button)[\"'][^>]*?>",
        re.IGNORECASE,
    )

    text_matches = re.finditer(
        r"(<[^>]+>[^<]*?instrumental[^<]*?</[^>]+>)",
        html_after,
        re.IGNORECASE,
    )
    for m in text_matches:
        candidates.append({"type": "text-match", "snippet": m.group(0)[:500]})

    attr_matches = re.finditer(
        r"(<[^>]*?(?:aria-label|data-testid|id|name|placeholder)\s*=\s*[\"'][^\"']*?instrumental[^\"']*?[\"'][^>]*?>)",
        html_after,
        re.IGNORECASE,
    )
    for m in attr_matches:
        candidates.append({"type": "attr-match", "snippet": m.group(0)[:500]})

    # role=switch 모음 (인스트루멘탈 토글일 가능성)
    switches = re.finditer(
        r"(<[^>]*?role\s*=\s*[\"']switch[\"'][^>]*?>)",
        html_after,
        re.IGNORECASE,
    )
    for m in switches:
        candidates.append({"type": "role-switch", "snippet": m.group(0)[:500]})

    # 중복 제거
    seen = set()
    deduped = []
    for c in candidates:
        key = c["snippet"]
        if key not in seen:
            seen.add(key)
            deduped.append(c)

    (OUT_DIR / "suno_instrumental_candidates.json").write_text(
        json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[7] 후보 {len(deduped)}건 저장")

    # 사람이 읽기 좋은 md
    md_lines = ["# Suno Instrumental 토글 후보 분석", ""]
    md_lines.append(f"- DOM after-dump: {len(html_after):,} chars")
    md_lines.append(f"- 후보: {len(deduped)}건")
    md_lines.append(f"- More Options 펼침: {more_clicked}")
    md_lines.append("")
    for i, c in enumerate(deduped, 1):
        md_lines.append(f"## #{i} ({c['type']})")
        md_lines.append("```html")
        md_lines.append(c["snippet"])
        md_lines.append("```")
        md_lines.append("")
    (OUT_DIR / "suno_instrumental_candidates.md").write_text(
        "\n".join(md_lines), encoding="utf-8"
    )
    print(f"[8] md 리포트 저장: {OUT_DIR / 'suno_instrumental_candidates.md'}")

    # JS로 'Instrumental' 텍스트 노드의 부모 트리 3-depth 추적
    js_probe = """
    var hits = [];
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    var n;
    while ((n = walker.nextNode())) {
        if (/instrumental/i.test(n.textContent)) {
            var el = n.parentElement;
            var trail = [];
            for (var d = 0; d < 4 && el; d++) {
                trail.push({
                    tag: el.tagName,
                    role: el.getAttribute('role'),
                    aria: el.getAttribute('aria-label'),
                    testid: el.getAttribute('data-testid'),
                    cls: (el.className || '').toString().slice(0, 80),
                    text: (el.textContent || '').slice(0, 60),
                    outer: el.outerHTML.slice(0, 280)
                });
                el = el.parentElement;
            }
            hits.push({text: n.textContent.trim().slice(0, 80), trail: trail});
        }
    }
    return hits;
    """
    try:
        hits = driver.execute_script(js_probe)
        (OUT_DIR / "suno_instrumental_text_hits.json").write_text(
            json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[9] 텍스트 노드 매칭 {len(hits)}건 저장")
    except Exception as e:
        print(f"[9] JS probe 실패: {e}")

    print("DONE")


if __name__ == "__main__":
    main()
