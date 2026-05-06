"""ActionChains로 Simple 버튼 실제 마우스 클릭. 5분 내 통하는지 단순 검증."""
from __future__ import annotations
import time, sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

opts = Options()
opts.debugger_address = "127.0.0.1:9222"
driver = webdriver.Chrome(options=opts)

driver.get("https://suno.com/create")
time.sleep(4)

# Simple 버튼 찾기
btns = driver.find_elements(By.XPATH, "//button[.//span[normalize-space()='Simple']]")
if not btns:
    print("FAIL: Simple 버튼 못 찾음"); sys.exit(1)
simple_btn = btns[0]
print(f"Simple 버튼 위치: {simple_btn.location} size={simple_btn.size}")

# 클릭 전 active 클래스 분포
def active_state():
    return driver.execute_script("""
    var out = {};
    ['Simple', 'Advanced', 'Sounds'].forEach(function(n) {
        var sp = Array.from(document.querySelectorAll('span')).find(function(s){return (s.textContent||'').trim()===n;});
        if (sp && sp.closest('button')) {
            out[n] = (sp.closest('button').className || '').indexOf('active') >= 0;
        }
    });
    var inst = document.querySelector('button[aria-label="Check this to generate an instrumental only song"]');
    if (inst) {
        var ps = inst.parentElement ? window.getComputedStyle(inst.parentElement) : null;
        out._instrumentalParentVisibility = ps ? ps.visibility : null;
    }
    return out;
    """)

print(f"클릭 전: {active_state()}")

# ActionChains로 실제 마우스 이벤트 발사
ac = ActionChains(driver)
ac.move_to_element(simple_btn).pause(0.3).click().perform()
time.sleep(2)

print(f"AC.click 후: {active_state()}")

# 안 통했으면 좌표 절대 클릭 시도
state = active_state()
if state.get('Simple'):
    print("WIN: Simple active")
else:
    rect = simple_btn.rect
    cx, cy = int(rect['x'] + rect['width']/2), int(rect['y'] + rect['height']/2)
    print(f"AC 좌표 클릭 시도 ({cx}, {cy})")
    # 절대 좌표 click via CDP
    driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
        "type": "mousePressed", "x": cx, "y": cy, "button": "left", "clickCount": 1
    })
    driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
        "type": "mouseReleased", "x": cx, "y": cy, "button": "left", "clickCount": 1
    })
    time.sleep(2)
    print(f"CDP click 후: {active_state()}")

driver.save_screenshot("data/debug/actionchains_after.png")
