"""Simple 모드 + Instrumental 탭 활성 상태에서 Create 버튼 위치/상태 진단."""
from __future__ import annotations
import time, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

opts = Options()
opts.debugger_address = "127.0.0.1:9222"
driver = webdriver.Chrome(options=opts)

driver.get("https://suno.com/create")
time.sleep(4)

# Simple 전환
simple = driver.find_element(By.XPATH, "//button[.//span[normalize-space()='Simple']]")
ActionChains(driver).move_to_element(simple).pause(0.3).click().perform()
time.sleep(2)

# Instrumental 탭
inst = driver.find_element(By.XPATH, '//button[@aria-label="Check this to generate an instrumental only song"]')
ActionChains(driver).move_to_element(inst).pause(0.3).click().perform()
time.sleep(2)

# SongDescription textarea 입력
style = "acoustic piano trio, bill evans inspired, modal jazz, brush drums, walking double bass"
result = driver.execute_script("""
function setNativeValue(el, val) {
    var setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
    setter.call(el, val);
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
}
var ta = null;
document.querySelectorAll('textarea').forEach(function(t) {
    var s = window.getComputedStyle(t);
    if (s.visibility === 'hidden' || t.offsetParent === null) return;
    if (t.maxLength === 3000) ta = t;
});
if (ta) {
    ta.focus();
    setNativeValue(ta, arguments[0]);
    return {len: ta.value.length, snippet: ta.value.slice(0, 30)};
}
return {error: 'no textarea'};
""", style)
print(f"Input: {result}")
time.sleep(1)

# Create 버튼 모든 후보 분석
btns = driver.execute_script("""
var out = [];
document.querySelectorAll('button').forEach(function(b) {
    var s = window.getComputedStyle(b);
    var rect = b.getBoundingClientRect();
    if (s.visibility === 'hidden' || b.offsetParent === null) return;
    var text = (b.textContent || '').trim();
    var aria = b.getAttribute('aria-label') || '';
    if (text.toLowerCase().includes('create') || aria.toLowerCase().includes('create')) {
        out.push({
            text: text.slice(0, 40),
            aria: aria,
            disabled: b.disabled,
            x: Math.round(rect.x), y: Math.round(rect.y),
            w: Math.round(rect.width), h: Math.round(rect.height),
            outer: b.outerHTML.slice(0, 250)
        });
    }
});
return out;
""")
print(f"\nCreate 버튼 후보: {len(btns)}개")
for b in btns:
    print(f"  [{b['x']:>3},{b['y']:>3}] {b['w']}x{b['h']} disabled={b['disabled']} aria={b['aria']!r} text={b['text']!r}")

driver.save_screenshot("data/debug/create_btn_state.png")
print("\nscreenshot: data/debug/create_btn_state.png")
