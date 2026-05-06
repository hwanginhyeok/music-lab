"""Custom 모드에서 Instrumental 토글 위치 추가 탐색.

가설: Custom 모드의 좌측 Lyrics 영역 헤더에 별도의 Instrumental 토글이 있다.
또는 More Options/Settings 안에 있다.
"""
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

probe = """
// 현재 모드 진단
var simpleBtn = Array.from(document.querySelectorAll('button')).find(function(b) {
    return (b.textContent || '').trim().toLowerCase() === 'simple';
});
var customBtn = Array.from(document.querySelectorAll('button')).find(function(b) {
    return (b.textContent || '').trim().toLowerCase() === 'custom';
});
var modeIndicator = {
    simpleVisible: simpleBtn ? (simpleBtn.offsetParent !== null) : false,
    customVisible: customBtn ? (customBtn.offsetParent !== null) : false,
    simpleText: simpleBtn ? simpleBtn.textContent.trim() : null,
    customText: customBtn ? customBtn.textContent.trim() : null
};

// 'Lyrics' 라벨/타이틀이 있는 영역 찾기 (좌측 패널)
var lyricsLabels = [];
Array.from(document.querySelectorAll('div, h1, h2, h3, h4, span')).forEach(function(el) {
    var t = (el.textContent || '').trim();
    if (t === 'Lyrics' && el.children.length === 0) {
        // 부모 컨테이너의 형제/자식에서 instrumental 관련 토글 찾기
        var container = el.closest('div[class]');
        if (!container) return;
        var siblings = Array.from(container.parentElement ? container.parentElement.children : []);
        var allButtons = container.parentElement ? Array.from(container.parentElement.querySelectorAll('button')).slice(0, 10) : [];
        var allInputs = container.parentElement ? Array.from(container.parentElement.querySelectorAll('input')).slice(0, 10) : [];
        lyricsLabels.push({
            text: t,
            containerClass: (container.className || '').toString().slice(0, 80),
            buttonCount: allButtons.length,
            buttonsNearby: allButtons.map(function(b) {
                var s = window.getComputedStyle(b);
                return {
                    text: (b.textContent || '').trim().slice(0, 50),
                    aria: b.getAttribute('aria-label'),
                    visible: s.visibility !== 'hidden' && s.display !== 'none' && b.offsetParent !== null,
                    outer: b.outerHTML.slice(0, 200)
                };
            }),
            inputsNearby: allInputs.map(function(i) {
                return {type: i.type, aria: i.getAttribute('aria-label'), checked: i.checked, role: i.getAttribute('role')};
            })
        });
    }
});

// 좌측 패널 영역 모든 visible 버튼 (id로 좌측 sidebar 추정)
var leftPanelButtons = [];
var allBtns = Array.from(document.querySelectorAll('button'));
allBtns.forEach(function(b) {
    var s = window.getComputedStyle(b);
    var rect = b.getBoundingClientRect();
    if (s.visibility === 'hidden' || s.display === 'none') return;
    if (b.offsetParent === null) return;
    if (rect.x > 500) return; // 좌측 패널만 (x < 500)
    leftPanelButtons.push({
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        w: Math.round(rect.width),
        h: Math.round(rect.height),
        text: (b.textContent || '').trim().slice(0, 40),
        aria: b.getAttribute('aria-label'),
        outer: b.outerHTML.slice(0, 200)
    });
});

// More Options / Settings 라벨 visible 여부
var moreOpts = [];
Array.from(document.querySelectorAll('button, div')).forEach(function(e) {
    var t = (e.textContent || '').trim();
    if (/More Options|Settings|Lyrics Settings/i.test(t) && t.length < 30) {
        var s = window.getComputedStyle(e);
        if (s.visibility !== 'hidden' && e.offsetParent !== null) {
            moreOpts.push({
                tag: e.tagName,
                text: t,
                aria: e.getAttribute('aria-label'),
                outer: e.outerHTML.slice(0, 200)
            });
        }
    }
});

// 좌측 패널의 Lyrics textarea 정확한 위치 + 그 위/옆 형제 element들
var lyricsTa = document.querySelector('textarea[data-testid="lyrics-textarea"]');
var lyricsHeader = null;
if (lyricsTa) {
    // Lyrics textarea의 부모로 거슬러 올라가며 헤더 영역 추적
    var p = lyricsTa.parentElement;
    var headers = [];
    for (var d = 0; d < 4 && p; d++) {
        // 형제 element 중 button 찾기
        var siblings = Array.from(p.parentElement ? p.parentElement.children : []);
        siblings.forEach(function(sib) {
            if (sib === p) return;
            var btns = Array.from(sib.querySelectorAll('button'));
            btns.forEach(function(btn) {
                var s = window.getComputedStyle(btn);
                if (s.visibility === 'hidden' || btn.offsetParent === null) return;
                headers.push({
                    depth: d,
                    text: (btn.textContent || '').trim().slice(0, 40),
                    aria: btn.getAttribute('aria-label'),
                    outer: btn.outerHTML.slice(0, 200)
                });
            });
        });
        p = p.parentElement;
    }
    lyricsHeader = headers.slice(0, 20);
}

return {
    modeIndicator: modeIndicator,
    lyricsLabels: lyricsLabels,
    leftPanelButtons: leftPanelButtons,
    moreOpts: moreOpts,
    lyricsHeader: lyricsHeader
};
"""

result = driver.execute_script(probe)
out_path = OUT / "suno_custom_mode_probe.json"
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[ok] probe 결과 저장: {out_path}")

# 핵심 인사이트만 출력
print("\n=== 모드 진단 ===")
print(json.dumps(result.get("modeIndicator"), ensure_ascii=False, indent=2))

print("\n=== 좌측 패널 visible 버튼 (x<500) ===")
for b in result.get("leftPanelButtons", [])[:30]:
    print(f"  [{b['x']:>3},{b['y']:>3}] aria={b['aria']!r:<60} text={b['text']!r}")

print("\n=== More Options / Settings 후보 ===")
for o in result.get("moreOpts", [])[:10]:
    print(f"  {o['tag']} text={o['text']!r} aria={o['aria']!r}")

print("\n=== Lyrics textarea 형제 영역 버튼 ===")
for h in result.get("lyricsHeader", []) or []:
    print(f"  d={h['depth']} aria={h['aria']!r:<60} text={h['text']!r}")
