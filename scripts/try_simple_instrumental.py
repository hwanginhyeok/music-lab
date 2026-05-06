"""Simple 모드 + Instrumental 탭 클릭 + 입력 영역 + Create 활성화 검증.
PoC #4 발주 직전 최종 진단. 크레딧 소비 X.
"""
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

# Simple 모드 전환
simple_btn = driver.find_element(By.XPATH, "//button[.//span[normalize-space()='Simple']]")
ActionChains(driver).move_to_element(simple_btn).pause(0.3).click().perform()
time.sleep(2)

# Instrumental 탭 클릭 (이제 visible)
inst_btn = driver.find_element(By.XPATH, '//button[@aria-label="Check this to generate an instrumental only song"]')
print(f"Instrumental btn displayed: {inst_btn.is_displayed()}")
ActionChains(driver).move_to_element(inst_btn).pause(0.3).click().perform()
time.sleep(2)
driver.save_screenshot("data/debug/simple_instrumental_clicked.png")

# 입력 영역 + Create 상태 진단
state = driver.execute_script("""
var visTas = [];
document.querySelectorAll('textarea').forEach(function(t) {
    var s = window.getComputedStyle(t);
    if (s.visibility === 'hidden' || t.offsetParent === null) return;
    var rect = t.getBoundingClientRect();
    visTas.push({
        placeholder: t.getAttribute('placeholder'),
        testid: t.getAttribute('data-testid'),
        maxLength: t.maxLength,
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        w: Math.round(rect.width)
    });
});

// Create 버튼 상태
var createBtns = Array.from(document.querySelectorAll('button')).filter(function(b) {
    return (b.textContent || '').trim() === 'Create' && b.offsetParent !== null;
});
var createState = createBtns.map(function(b) { return {disabled: b.disabled, text: b.textContent.trim()}; });

// Instrumental 탭 active 상태
var instBtn = document.querySelector('button[aria-label="Check this to generate an instrumental only song"]');
var instActive = instBtn ? (instBtn.className || '').indexOf('active') >= 0 : null;

return {visibleTas: visTas, createState: createState, instActive: instActive};
""")
print(json.dumps(state, ensure_ascii=False, indent=2))
