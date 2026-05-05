#!/bin/bash
# GDrive 단방향 sync — md/txt/json만 업로드, mp3/wav/mp4 제외
# SSOT는 로컬. GDrive는 사본/공유 채널.
# 사용법:
#   bash scripts/sync_gdrive.sh                  # 전체 sync
#   bash scripts/sync_gdrive.sh 18_sulbyeong_natda  # 특정 앨범만

set -u
cd /home/window11/music-lab

# GDrive 폴더 컨벤션 — 로컬 dir → GDrive 폴더명
declare -A GDRIVE_NAMES=(
    ["01_봄이라고_부를게"]="4-1 봄을 통해 너를 봄"
    ["14_geuriumi"]="5-14 그리움만 쌓이게"
    ["18_sulbyeong_natda"]="5-18 술병이 났다"
)

INCLUDE_FLAGS='--include "*.md" --include "*.txt" --include "*.json"'
EXCLUDE_FLAGS='--exclude "raw/**" --exclude "**/raw/**" --exclude "release/**" --exclude "suno/**" --exclude "_tools/**" --exclude "**/__pycache__/**"'

sync_album() {
    local local_dir="$1"
    local gdrive_name="${GDRIVE_NAMES[$local_dir]:-}"
    if [ -z "$gdrive_name" ]; then
        echo "⚠️  매핑 없음: songs/$local_dir — GDRIVE_NAMES에 등록 필요"
        return 1
    fi
    if [ ! -d "songs/$local_dir" ]; then
        echo "⚠️  로컬 디렉토리 없음: songs/$local_dir"
        return 1
    fi
    echo "→ songs/$local_dir → gdrive:music-lab/$gdrive_name"
    rclone copy "songs/$local_dir/" "gdrive:music-lab/$gdrive_name/" \
        --include "*.md" --include "*.txt" --include "*.json" \
        --exclude "raw/**" --exclude "**/raw/**" \
        --exclude "release/**" --exclude "suno/**" \
        --exclude "_tools/**" --exclude "**/__pycache__/**" \
        --exclude "*.deb" --exclude "*.zip"
    echo "  ✅"
}

sync_docs() {
    echo "→ docs/albums/ → gdrive:music-lab/_docs/albums/"
    rclone copy docs/albums/ "gdrive:music-lab/_docs/albums/" --include "*.md"
    echo "  ✅"
    echo "→ docs/albums/INDEX.md → gdrive:music-lab/_INDEX.md"
    rclone copyto docs/albums/INDEX.md "gdrive:music-lab/_INDEX.md"
    echo "  ✅"
    echo "→ docs/data-management.md → gdrive:music-lab/_docs/"
    rclone copy docs/data-management.md "gdrive:music-lab/_docs/"
    echo "  ✅"
}

# 정책 위반 검사 (mp3 등이 GDrive에 잘못 올라간 게 없는지)
check_policy() {
    echo "→ GDrive 정책 위반 검사 (mp3/wav/mp4 노출 여부)..."
    local violations=$(rclone lsf -R gdrive:music-lab/ --files-only 2>/dev/null | grep -E "\.(mp3|wav|mp4|m4a|ogg|flac)$" | grep -v "^_admin/" || true)
    if [ -n "$violations" ]; then
        echo "  ⚠️  정책 위반 파일 발견:"
        echo "$violations" | sed 's/^/    /'
        echo "  → rclone delete 또는 rclone purge 로 정리 필요"
    else
        echo "  ✅ 위반 없음"
    fi
}

if [ $# -eq 0 ]; then
    echo "=== 전체 GDrive sync ==="
    for dir in "${!GDRIVE_NAMES[@]}"; do
        sync_album "$dir"
    done
    sync_docs
    check_policy
else
    sync_album "$1"
fi

echo ""
echo "=== sync 완료 $(date +%T) ==="
