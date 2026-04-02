#!/bin/bash
# VNC + noVNC 서버 시작 스크립트
# Suno 자동화용 가상 디스플레이 + 웹 VNC 접속

DISPLAY_NUM=":1"
VNC_PORT=5901
NOVNC_PORT=6080
VNC_PASSWD_FILE="$HOME/.vnc/passwd"

echo "=== Suno VNC 서버 시작 ==="

# 기존 프로세스 정리
pkill -f "Xtigervnc $DISPLAY_NUM" 2>/dev/null
pkill -f "websockify.*$NOVNC_PORT" 2>/dev/null
sleep 1

# VNC 비밀번호 설정 (없으면 생성)
if [ ! -f "$VNC_PASSWD_FILE" ]; then
    mkdir -p ~/.vnc
    echo "suno" | vncpasswd -f > "$VNC_PASSWD_FILE"
    chmod 600 "$VNC_PASSWD_FILE"
    echo "VNC 비밀번호 생성됨 (suno)"
fi

# fluxbox xstartup
if [ ! -f ~/.vnc/xstartup ]; then
    cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
fluxbox &
EOF
    chmod +x ~/.vnc/xstartup
fi

# 1. Xtigervnc 시작 (TCP만, unix 소켓 없이 — WSL2 호환)
rm -f /tmp/.X1-lock 2>/dev/null
Xtigervnc $DISPLAY_NUM \
    -geometry 1280x720 -depth 24 \
    -rfbport $VNC_PORT \
    -rfbauth "$VNC_PASSWD_FILE" \
    -SecurityTypes VncAuth \
    -nolisten unix \
    -AlwaysShared \
    &>/tmp/vnc.log &
sleep 2

if ! ss -tlnp | grep -q ":$VNC_PORT"; then
    echo "❌ VNC 서버 시작 실패"
    cat /tmp/vnc.log
    exit 1
fi
echo "✅ VNC 서버: 포트 $VNC_PORT"

# 2. fluxbox 윈도우매니저
DISPLAY=$DISPLAY_NUM fluxbox &>/dev/null &
sleep 1
echo "✅ fluxbox 시작"

# 3. noVNC (websockify)
websockify --web=/usr/share/novnc/ $NOVNC_PORT localhost:$VNC_PORT &>/tmp/novnc.log &
sleep 1

if ! ss -tlnp | grep -q ":$NOVNC_PORT"; then
    echo "❌ noVNC 시작 실패"
    exit 1
fi
echo "✅ noVNC: 포트 $NOVNC_PORT"

echo ""
echo "=== 접속 방법 ==="
echo "1. SSH 터널: ssh -N -L $NOVNC_PORT:127.0.0.1:$NOVNC_PORT window11@100.84.144.16"
echo "2. 브라우저: http://localhost:$NOVNC_PORT/vnc.html"
echo "3. VNC 비밀번호: suno"
echo ""
echo "=== Suno 자동화 실행 ==="
echo "python3 suno_pipeline.py --title \"곡제목\" --prompt-file songs/01_봄이라고_부를게/suno_prompt_final.md"
