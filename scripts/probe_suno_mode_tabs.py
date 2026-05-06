"""Suno Create 페이지 — 3-탭 모드 스위치 (Audio/Lyrics/Instrumental) 셀렉터 추출.

전제: Instrumental 버튼은 DOM에 있지만 visibility:hidden. 부모 컨테이너가 mode tab group.
이 스크립트는 hidden 부모를 거슬러 올라가며 'AudioLyricsInstrumental' 텍스트를 가진
컨테이너를 찾고, 그 자식 3개 버튼/div의 셀렉터를 모두 추출.
"""
from __future__ import annotations
import json, time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

OUT = Path("songs/14_geuriumi/tracks/_tools")
OUT.mkdir(parents=True, exist_ok=True)

opts = Options()
opts.debugger_address = "127.0.0.1:9222"
driver = webdriver.Chrome(options=opts)

driver.get("https://suno.com/create")
time.sleep(4)

# Advanced 모드 진입
try:
    for b in driver.find_elements(By.XPATH, "//button[contains(., 'Advanced')]"):
        if b.is_displayed():
            b.click()
            time.sleep(2)
            break
except Exception:
    pass

probe = """
// Instrumental 버튼에서 출발해 부모 트리를 거슬러 올라가
// '3-탭 그룹' 컨테이너를 찾고, 그 자식 button/role 3개를 모두 분석.
var instBtn = document.querySelector('button[aria-label="Check this to generate an instrumental only song"]');
if (!instBtn) return {error: 'instrumental button not found'};

// 자기 자신과 부모들의 가시성 추적
var visibilityChain = [];
var el = instBtn;
for (var d = 0; d < 8 && el; d++) {
    var s = window.getComputedStyle(el);
    visibilityChain.push({
        depth: d,
        tag: el.tagName,
        cls: (el.className || '').toString().slice(0, 80),
        visibility: s.visibility,
        display: s.display,
        opacity: s.opacity,
        ariaLabel: el.getAttribute('aria-label'),
        role: el.getAttribute('role'),
        dataState: el.getAttribute('data-state'),
        textPreview: (el.textContent || '').replace(/\\s+/g, '').slice(0, 80)
    });
    el = el.parentElement;
}

// 3-탭 그룹 컨테이너 추정: textContent에 'AudioLyricsInstrumental' (공백 무시) 포함
var tabGroup = null;
el = instBtn;
for (var d = 0; d < 8 && el; d++) {
    var t = (el.textContent || '').replace(/\\s+/g, '');
    if (t.indexOf('AudioLyricsInstrumental') !== -1) {
        tabGroup = el;
        break;
    }
    el = el.parentElement;
}

var tabsInfo = null;
if (tabGroup) {
    // 자식들 중 button 태그 모두 추출
    var childButtons = Array.from(tabGroup.querySelectorAll('button'));
    tabsInfo = {
        groupTag: tabGroup.tagName,
        groupClass: (tabGroup.className || '').toString().slice(0, 120),
        groupRole: tabGroup.getAttribute('role'),
        buttonCount: childButtons.length,
        buttons: childButtons.map(function(b) {
            var s = window.getComputedStyle(b);
            return {
                ariaLabel: b.getAttribute('aria-label'),
                role: b.getAttribute('role'),
                dataState: b.getAttribute('data-state'),
                ariaSelected: b.getAttribute('aria-selected'),
                ariaPressed: b.getAttribute('aria-pressed'),
                textContent: (b.textContent || '').replace(/\\s+/g, '').slice(0, 50),
                visibility: s.visibility,
                display: s.display,
                offsetVisible: b.offsetParent !== null,
                outer: b.outerHTML.slice(0, 320)
            };
        })
    };
}

// 추가: 'Custom' 버튼 (Advanced 모드 진입용) 후보
var customCandidates = [];
['button', 'div', 'span'].forEach(function(tag) {
    Array.from(document.querySelectorAll(tag)).forEach(function(e) {
        var t = (e.textContent || '').replace(/\\s+/g, '').toLowerCase();
        if (t === 'custom' || t === 'simple') {
            var s = window.getComputedStyle(e);
            customCandidates.push({
                tag: e.tagName,
                text: (e.textContent || '').trim(),
                ariaLabel: e.getAttribute('aria-label'),
                visibility: s.visibility,
                display: s.display,
                offsetVisible: e.offsetParent !== null,
                outer: e.outerHTML.slice(0, 200)
            });
        }
    });
});

// 활성 탭 진단 — 현재 어느 탭이 active인가
var activeTab = null;
if (tabGroup) {
    Array.from(tabGroup.querySelectorAll('button')).forEach(function(b) {
        var ds = b.getAttribute('data-state');
        var as = b.getAttribute('aria-selected');
        var ap = b.getAttribute('aria-pressed');
        if (ds === 'active' || ds === 'on' || as === 'true' || ap === 'true') {
            activeTab = {
                ariaLabel: b.getAttribute('aria-label'),
                text: (b.textContent || '').replace(/\\s+/g, '').slice(0, 50),
                dataState: ds, ariaSelected: as, ariaPressed: ap
            };
        }
    });
}

return {
    visibilityChain: visibilityChain,
    tabsInfo: tabsInfo,
    customCandidates: customCandidates.slice(0, 6),
    activeTab: activeTab
};
"""

result = driver.execute_script(probe)
out_path = OUT / "suno_mode_tabs_probe.json"
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[ok] probe 결과 저장: {out_path}")
print(json.dumps(result, ensure_ascii=False, indent=2)[:6000])
