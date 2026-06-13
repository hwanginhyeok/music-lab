# Current Tasks

| # | Task | Start Date | blocked | Notes |
|---|--------|--------|---------|------|
| 5-17 | Colorless Odorless Empty Bottle — generate 9 tracks + select best take | 2026-05-15 | — | Track 1~9 v1/v2 generation complete (2026-05-15). Next: listen while on the move → select best take → post-process (-14 LUFS) → publish to YouTube |
| 5-19 | Daylight Hours post-processing + release | 2026-05-10 | ⏸️ On hold | 15 K-pop tracks. v1.mp3 complete (GDrive). Next: select best take → post-process (-14 LUFS) → publish to YouTube |
| 5-20 | Electric Feelings post-processing + release | 2026-05-10 | ⏸️ On hold | 15 pop-rock variant tracks. v1.mp3 complete (GDrive). Next: select best take → post-process (-14 LUFS) → publish to YouTube |
| 7-1 | YouTube posting copy auto-generation pipeline | 2026-04-23 | — | P1. Song meta → Claude API → title/description/hashtags/timestamps. Phase 1 CLI → Phase 2 Telegram /youtube_copy → Phase 3 uploader auto-injection |
| PIPE-AUTO | 음악 풀자동 파이프라인 — 잔여 통합 | 2026-06-14 | ⏸️ (c) VNC 의존 | **Phase 2~4 + HTML 저널 + 풀 파이프라인 조립 + F02 텔레그램 후보카드/`/select`/`/resume` 라이브 완료(→FINISHED)**. 봇 active 가동 중. 잔여: **(b)** 저널 렌더러에 Phase 4 노드(후처리/영상/업로드) 타임라인 표시 추가(소규모, `autopilot/journal.py`) **(c)** 실 VNC(:1) e2e 1회 — 기획→생성→선택→후처리→영상→업로드 실런(⏸️ VNC+실생성+캡차 이벤트터치 의존, PM이 환경 준비 후). 설계 SSOT `plans/PIPE-AUTO.md` |

## 7-1 Detailed Spec

### Scope
- (a) Song metadata (title/concept/lyrics/genre/artwork) → Claude API → generate YouTube description
- (b) Title template: `{song name} — {artist/project name}` or `{album name} Track N: {song name}`
- (c) Description structure: song intro → lyrics → credits (Suno generation / post-processing) → album info → hashtags → license
- (d) Auto-generate hashtags (10~15 based on genre/mood/keywords)
- (e) Auto-generate timestamps (for multi-track album videos)
- (f) Thumbnail copy (2-line title summary) option

### Input/Output
- **Input**: song directory (`songs/{NN}_{song name}/` — meta json + lyrics md + suno prompt md + mix result)
- **Output**: `youtube_copy/{song name}.md` + `{song name}.json` (structured title/description/hashtags)

### Integration
- Telegram bot `/youtube_copy` command (same pattern as Suno natural-language commands)
- The `youtube_uploader` script auto-injects this result

### Phase breakdown
- **Phase 1**: CLI script — `python scripts/generate_youtube_copy.py <song directory>`
- **Phase 2**: Telegram bot command integration
- **Phase 3**: integrate auto-injection into the upload pipeline
