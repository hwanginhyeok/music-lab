"""ActionChains로 Create 버튼 클릭 → 곡 생성 시작 여부 검증.
Style 86자 이미 입력된 상태 가정. 이전 probe 직후 실행.
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

# 현재 페이지가 /create인지 + Style이 입력됐는지 검증
state = driver.execute_script("""
var ta = null;
document.querySelectorAll('textarea').forEach(function(t) {
    if (t.maxLength === 3000 && t.offsetParent !== null) ta = t;
});
var createBtn = Array.from(document.querySelectorAll('button')).find(function(b) {
    return (b.getAttribute('aria-label') || '').toLowerCase() === 'create song' && b.offsetParent !== null;
});
return {
    url: location.href,
    inputLen: ta ? ta.value.length : -1,
    inputSnippet: ta ? ta.value.slice(0, 40) : null,
    createDisabled: createBtn ? createBtn.disabled : null
};
""")
print(f"State: {state}")

if state.get('inputLen', 0) < 10:
    print("Style 입력이 비어있음 — probe_simple_create_btn.py 먼저 실행 필요"); exit(1)

# Suno API로 기존 곡 ID 수집
import sys, os
sys.path.insert(0, '.')
from suno_download import SunoAPI
api = SunoAPI()
existing = {s["id"] for s in api.get_songs(page=0) if s.get("id")}
print(f"기존 곡 {len(existing)}개")

# Create 버튼 ActionChains 클릭
create_btn = driver.find_element(By.XPATH, "//button[@aria-label='Create song']")
print(f"Create 버튼 위치: {create_btn.location} disabled={create_btn.get_attribute('disabled')}")

ActionChains(driver).move_to_element(create_btn).pause(0.5).click().perform()
print("ActionChains.click() 실행 완료")
time.sleep(3)

# 30초 동안 폴링 — 새 곡 ID 등장하는지
import time as _t
start = _t.time()
detected = False
while _t.time() - start < 30:
    try:
        api.refresh_jwt()
        current = api.get_songs(page=0)
        new_ids = [s for s in current if s.get("id") and s["id"] not in existing]
        if new_ids:
            print(f"\n*** WIN — 새 곡 {len(new_ids)}개 감지 ***")
            for s in new_ids:
                print(f"  id={s['id']} status={s.get('status')} title={s.get('title')!r}")
            detected = True
            break
    except Exception as e:
        print(f"  poll err: {e}")
    _t.sleep(3)

if not detected:
    print("\n30초 내 새 곡 안 나옴 — Create 클릭이 React에 안 갔거나 백엔드 거부")
    driver.save_screenshot("data/debug/create_actionchains_no_response.png")
