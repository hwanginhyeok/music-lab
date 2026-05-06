"""Simple 모드 진입 → Instrumental 탭 visible 확인 → 입력 영역 분석."""
from __future__ import annotations
import json, time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

OUT = Path("songs/14_geuriumi/tracks/_tools")

opts = Options()
opts.debugger_address = "127.0.0.1:9222"
driver = webdriver.Chrome(options=opts)

driver.get("https://suno.com/create")
time.sleep(3)

# 좌상단 'Simple' 버튼 클릭 (좌표 약 219,17 영역)
clicked = driver.execute_script("""
var btns = Array.from(document.querySelectorAll('button, span, div'));
var simpleBtn = btns.find(function(b) {
    var t = (b.textContent || '').trim();
    if (t !== 'Simple') return false;
    var s = window.getComputedStyle(b);
    if (s.visibility === 'hidden' || s.display === 'none') return false;
    return b.offsetParent !== null;
});
if (simpleBtn) {
    // 실제 클릭 가능한 부모로 거슬러 올라가기
    var clickTarget = simpleBtn.tagName === 'BUTTON' ? simpleBtn : simpleBtn.closest('button') || simpleBtn;
    clickTarget.click();
    return {clicked: true, tag: clickTarget.tagName, outer: clickTarget.outerHTML.slice(0, 200)};
}
return {clicked: false};
""")
print(f"[1] Simple click: {clicked}")
time.sleep(2)

driver.save_screenshot("data/debug/simple_mode_after_click.png")

# 변화 확인
probe = """
// Instrumental 토글 가시성 재측정
var instBtn = document.querySelector('button[aria-label="Check this to generate an instrumental only song"]');
var instInfo = null;
if (instBtn) {
    var s = window.getComputedStyle(instBtn);
    var ps = instBtn.parentElement ? window.getComputedStyle(instBtn.parentElement) : null;
    instInfo = {
        visibility: s.visibility,
        display: s.display,
        parentVisibility: ps ? ps.visibility : null,
        offsetVisible: instBtn.offsetParent !== null,
        rect: (function(){var r=instBtn.getBoundingClientRect(); return {x:r.x, y:r.y, w:r.width, h:r.height};})()
    };
}

// Simple 모드 진입 후 좌측 패널의 모든 textarea + button
var leftElements = [];
Array.from(document.querySelectorAll('textarea, button, input')).forEach(function(el) {
    var s = window.getComputedStyle(el);
    var rect = el.getBoundingClientRect();
    if (s.visibility === 'hidden' || s.display === 'none') return;
    if (el.offsetParent === null) return;
    if (rect.x > 600 || rect.y > 800) return;
    leftElements.push({
        tag: el.tagName,
        x: Math.round(rect.x), y: Math.round(rect.y),
        w: Math.round(rect.width), h: Math.round(rect.height),
        text: (el.textContent || '').trim().slice(0, 40),
        aria: el.getAttribute('aria-label'),
        placeholder: el.getAttribute('placeholder'),
        testid: el.getAttribute('data-testid')
    });
});

// 현재 모드 시각 단서
var modeButtons = [];
Array.from(document.querySelectorAll('button, span')).forEach(function(b) {
    var t = (b.textContent || '').trim();
    if (['Simple', 'Advanced', 'Sounds'].includes(t)) {
        var s = window.getComputedStyle(b);
        if (s.visibility !== 'hidden' && b.offsetParent !== null) {
            // 활성화 상태 — 부모 button의 클래스에서 추정
            var parent = b.closest('button');
            modeButtons.push({
                text: t,
                tag: b.tagName,
                parentClass: parent ? (parent.className || '').toString().slice(0, 80) : null,
                parentDataState: parent ? parent.getAttribute('data-state') : null,
                parentDataActive: parent ? parent.getAttribute('data-active') : null
            });
        }
    }
});

return {
    instInfo: instInfo,
    leftElements: leftElements,
    modeButtons: modeButtons
};
"""
result = driver.execute_script(probe)
out_path = OUT / "suno_simple_mode_probe.json"
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"\n=== Instrumental 토글 (Simple 모드 진입 후) ===")
print(json.dumps(result.get("instInfo"), ensure_ascii=False, indent=2))

print("\n=== 좌측 visible 요소 (x<600, y<800) ===")
for e in result.get("leftElements", [])[:25]:
    print(f"  [{e['x']:>3},{e['y']:>3}] {e['tag']:<8} aria={e['aria']!r:<55} placeholder={e['placeholder']!r}")

print("\n=== 모드 버튼 활성화 단서 ===")
for m in result.get("modeButtons", []):
    print(f"  {m['text']:<10} dataState={m['parentDataState']!r} dataActive={m['parentDataActive']!r}")

# 추가: Simple 모드에서 Instrumental 탭 클릭 시도
inst_click = driver.execute_script("""
var b = document.querySelector('button[aria-label="Check this to generate an instrumental only song"]');
if (!b) return 'not-found';
var s = window.getComputedStyle(b);
if (s.visibility === 'hidden' || b.offsetParent === null) return 'hidden';
b.click();
return 'clicked';
""")
print(f"\n=== Instrumental 탭 클릭 시도: {inst_click} ===")
time.sleep(2)
driver.save_screenshot("data/debug/simple_mode_after_instrumental_click.png")

# 클릭 후 변화 확인
post = driver.execute_script("""
var lyricsTa = document.querySelectorAll('textarea[data-testid="lyrics-textarea"]');
var lyricsState = Array.from(lyricsTa).map(function(t) {
    var s = window.getComputedStyle(t);
    return {visibility: s.visibility, display: s.display, offsetVisible: t.offsetParent !== null};
});
// 새로 visible 텍스트영역
var visibleTas = [];
document.querySelectorAll('textarea').forEach(function(t) {
    var s = window.getComputedStyle(t);
    if (s.visibility !== 'hidden' && t.offsetParent !== null) {
        visibleTas.push({
            placeholder: t.getAttribute('placeholder'),
            testid: t.getAttribute('data-testid'),
            maxLength: t.maxLength
        });
    }
});
// Create 버튼 활성화
var createBtn = Array.from(document.querySelectorAll('button')).find(function(b) {
    return (b.textContent || '').trim() === 'Create';
});
return {
    lyricsState: lyricsState,
    visibleTas: visibleTas,
    createEnabled: createBtn ? !createBtn.disabled : null
};
""")
print(f"\n=== Instrumental 탭 클릭 후 ===")
print(json.dumps(post, ensure_ascii=False, indent=2))
