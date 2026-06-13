"""PIPE-F14: bot.py 단일 인스턴스 잠금 검증.

실제 서브프로세스 2개를 띄워 2번째가 즉시 종료(exit 1)하는지 증명한다.
프로덕션 lock 경로가 아닌 TMP lock 경로를 사용해 운영 중인 systemd 봇은 건드리지 않는다.
"""

import os
import subprocess
import sys
import tempfile
import time

import pytest

# bot import 시 module-level에서 TELEGRAM_BOT_TOKEN을 요구하므로 더미 토큰 주입.
# 잠금 헬퍼 자체는 토큰이 필요 없다.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_WORKER = (
    "import sys, time, bot; "
    "bot._acquire_single_instance_lock(sys.argv[1]); "
    "open(sys.argv[1] + '.acquired', 'w').close(); "  # 획득 신호
    "time.sleep(float(sys.argv[2]))"
)


def _spawn_worker(lock_path: str, sleep_s: float) -> subprocess.Popen:
    env = dict(os.environ)
    env.setdefault("TELEGRAM_BOT_TOKEN", "dummy:token")
    return subprocess.Popen(
        [sys.executable, "-c", _WORKER, lock_path, str(sleep_s)],
        cwd=_REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _wait_acquired(lock_path: str, timeout: float = 8.0) -> None:
    """worker가 잠금을 실제로 획득(.acquired 마커 생성)할 때까지 대기."""
    deadline = time.time() + timeout
    marker = lock_path + ".acquired"
    while time.time() < deadline:
        if os.path.exists(marker):
            return
        time.sleep(0.05)
    raise AssertionError("worker가 시간 내 잠금을 획득하지 못함")


def test_second_instance_exits_immediately():
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = os.path.join(tmp, ".test-bot.lock")

        # worker #1: 잠금 보유 후 3초 sleep
        w1 = _spawn_worker(lock_path, 3.0)
        try:
            _wait_acquired(lock_path)
            assert w1.poll() is None, "worker #1이 잠금 보유 중이어야 함"

            # worker #2: 같은 lock 경로 → 즉시 종료(exit 1) 기대
            w2 = _spawn_worker(lock_path, 3.0)
            rc2 = w2.wait(timeout=3.0)
            out2 = w2.stderr.read().decode("utf-8", "replace")
            assert rc2 == 1, f"worker #2는 exit 1 이어야 함 (실제 {rc2})\n{out2}"
            assert "중복 실행 차단" in out2, f"중복 차단 로그 누락:\n{out2}"

            # worker #1은 여전히 살아있어야 함
            assert w1.poll() is None, "worker #1은 worker #2 종료 시점에 살아있어야 함"
        finally:
            w1.wait(timeout=6.0)

        # worker #1 종료 → 잠금 해제됨 → 3번째 획득 성공해야 함
        os.path.exists(lock_path + ".acquired") and os.remove(lock_path + ".acquired")
        w3 = _spawn_worker(lock_path, 0.2)
        try:
            _wait_acquired(lock_path)  # 마커 생성 = 획득 성공
            rc3 = w3.wait(timeout=3.0)
            assert rc3 == 0, "잠금 해제 후 3번째 인스턴스는 정상 획득(exit 0)해야 함"
        finally:
            if w3.poll() is None:
                w3.kill()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
