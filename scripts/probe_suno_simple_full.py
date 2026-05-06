"""Simple 모드 진입 후 Instrumental 탭 visible 확인 + Model 5.5 셀렉터 추출.

이전 probe(probe_suno_simple_mode.py)에서 Simple 클릭이 효과 없었던 원인:
'Simple' span을 클릭했을 때 부모 button의 data-trigger-disabled 때문에 disabled 였음.
이번엔 더 정밀하게 모드 토글 그룹 탐색 + 클릭 + 검증.
"""
from __future__ import annotations
import json, time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

OUT = Path("songs/14_geuriumi/tracks/_tools")
DEBUG = Path("data/debug")

opts = Options()
opts.debugger_address = "127.0.0.1:9222"
driver = webdriver.Chrome(options=opts)

driver.get("https://suno.com/create")
time.sleep(4)
driver.save_screenshot(str(DEBUG / "step0_initial.png"))

# 1) Simple/Advanced/Sounds 모드 토글 그룹의 부모 컨테이너 찾기 + 클릭 가능 여부 분석
mode_info = driver.execute_script("""
var result = {modes: [], parentGroup: null};
var modeNames = ['Simple', 'Advanced', 'Sounds'];
modeNames.forEach(function(name) {
    var spans = Array.from(document.querySelectorAll('span'));
    var span = spans.find(function(s) {
        return (s.textContent || '').trim() === name &&
               s.offsetParent !== null;
    });
    if (!span) {
        result.modes.push({name: name, found: false});
        return;
    }
    var btn = span.closest('button');
    if (!btn) {
        result.modes.push({name: name, found: true, hasButton: false});
        return;
    }
    var s = window.getComputedStyle(btn);
    result.modes.push({
        name: name,
        found: true,
        hasButton: true,
        disabled: btn.disabled,
        triggerDisabled: btn.getAttribute('data-trigger-disabled'),
        ariaPressed: btn.getAttribute('aria-pressed'),
        ariaDisabled: btn.getAttribute('aria-disabled'),
        dataState: btn.getAttribute('data-state'),
        className: (btn.className || '').toString().slice(0, 80),
        outer: btn.outerHTML.slice(0, 280)
    });
});

// 부모 그룹 컨테이너 (Simple 버튼의 closest div with role=tablist 또는 className 기준)
var simpleSpan = Array.from(document.querySelectorAll('span')).find(function(s) {
    return (s.textContent || '').trim() === 'Simple';
});
if (simpleSpan) {
    var simpleBtn = simpleSpan.closest('button');
    if (simpleBtn && simpleBtn.parentElement) {
        result.parentGroup = {
            tag: simpleBtn.parentElement.tagName,
            role: simpleBtn.parentElement.getAttribute('role'),
            className: (simpleBtn.parentElement.className || '').toString().slice(0, 100),
            outer: simpleBtn.parentElement.outerHTML.slice(0, 600)
        };
    }
}
return result;
""")
print("=== 모드 토글 분석 ===")
print(json.dumps(mode_info, ensure_ascii=False, indent=2))

# 2) Simple 버튼 클릭 시도 (disabled 아니면)
clicked = driver.execute_script("""
var span = Array.from(document.querySelectorAll('span')).find(function(s) {
    return (s.textContent || '').trim() === 'Simple' && s.offsetParent !== null;
});
if (!span) return 'simple-span-not-found';
var btn = span.closest('button');
if (!btn) return 'simple-btn-not-found';
if (btn.getAttribute('data-trigger-disabled') !== null && btn.getAttribute('data-trigger-disabled') !== 'false') {
    // disabled — 부모 컨테이너 자체가 다른 진입점일 수 있음. 직접 클릭 강행
    btn.removeAttribute('data-trigger-disabled');
}
// dispatch real click
var evt = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});
btn.dispatchEvent(evt);
btn.click();
return 'clicked';
""")
print(f"\n[Simple 클릭 시도]: {clicked}")
time.sleep(2)
driver.save_screenshot(str(DEBUG / "step1_after_simple_click.png"))

# 3) URL 변화 확인 (Suno는 mode를 URL 쿼리로 가지기도)
print(f"\n[URL after click]: {driver.current_url}")

# 4) Simple 모드 URL 직접 진입 (Suno가 ?mode=simple 같은 패턴 가질 가능성)
candidate_urls = [
    "https://suno.com/create?mode=simple",
    "https://suno.com/create/simple",
    "https://suno.com/create?advanced=false",
]
for url in candidate_urls:
    driver.get(url)
    time.sleep(3)
    final_url = driver.current_url
    inst_visible = driver.execute_script("""
    var b = document.querySelector('button[aria-label="Check this to generate an instrumental only song"]');
    if (!b) return null;
    var s = window.getComputedStyle(b);
    var ps = b.parentElement ? window.getComputedStyle(b.parentElement) : null;
    return {
        visibility: s.visibility,
        parentVisibility: ps ? ps.visibility : null,
        offsetVisible: b.offsetParent !== null
    };
    """)
    print(f"\n[{url}] → {final_url}")
    print(f"  Instrumental btn: {inst_visible}")
    driver.save_screenshot(str(DEBUG / f"step2_{url.split('?')[-1].replace('=','_')[:30]}.png"))
    if inst_visible and inst_visible.get('parentVisibility') != 'hidden':
        print(f"  *** WIN — Instrumental 토글 visible ***")
        break

# 5) Model 5.5 / 모델 셀렉터 후보 추출
model_info = driver.execute_script("""
// 모델 텍스트 후보: '5.5', 'v5.5', 'Chirp 5.5', 'Model'
var candidates = [];
var texts = ['5.5', 'v5.5', 'Chirp', 'Model'];
texts.forEach(function(txt) {
    Array.from(document.querySelectorAll('button, div, span')).forEach(function(e) {
        var t = (e.textContent || '').trim();
        if (t.length > 30) return;
        if (t.indexOf(txt) === -1) return;
        var s = window.getComputedStyle(e);
        if (s.visibility === 'hidden' || e.offsetParent === null) return;
        candidates.push({
            tag: e.tagName,
            text: t,
            aria: e.getAttribute('aria-label'),
            outer: e.outerHTML.slice(0, 220),
            x: Math.round(e.getBoundingClientRect().x),
            y: Math.round(e.getBoundingClientRect().y)
        });
    });
});
// 중복 제거
var seen = {};
return candidates.filter(function(c) {
    var k = c.text + c.x + c.y;
    if (seen[k]) return false;
    seen[k] = true;
    return true;
}).slice(0, 20);
""")
print("\n=== Model 셀렉터 후보 ===")
for c in model_info:
    print(f"  [{c['x']:>3},{c['y']:>3}] {c['tag']:<8} text={c['text']!r:<25} aria={c['aria']!r}")

(OUT / "suno_simple_full_probe.json").write_text(
    json.dumps({"modes": mode_info, "modelCandidates": model_info}, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print(f"\n[saved] {OUT/'suno_simple_full_probe.json'}")
