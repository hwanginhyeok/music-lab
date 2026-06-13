# PIPE-AUTO — 음악 제작 풀 자동화 파이프라인 (PLAN v4)

> 사용자는 "앨범 기획"만, 나머지(작사→프롬프트→생성→후보추림→[청취선택]→후처리→영상→unlisted 업로드)는 자동.
> 사람 터치 **3개**: ① 앨범 기획 ② 후보 선택(청취) ③ public 전환.

이 문서는 PM이 Claude + Codex + GLM **3-way 교차검증으로 확정한 설계**의 SSOT다.

---

## 1. 4대 아키텍처 결정 (확정 — 변경 금지)

| # | 결정 | 근거 |
|---|------|------|
| 1 | 오케스트레이션 = **자체 state machine** | LangGraph 기각(3-way 만장일치). 월 1~2앨범 규모에 과함 + API 파편화 + `interrupt()` 함정. SQLite를 canonical state로. |
| 2 | 생성 = **서드파티 Suno API** | hCaptcha로 자체 무인생성 불가 확정(DIFFICULTY D-001). Phase 2엔 stub만. 실제 연동은 Phase 1 PoC(API 키 대기 중). |
| 3 | 모니터링 = **LangSmith SDK 독립 연동** | `@traceable`만 사용, LangGraph 없이. 키 없으면 no-op fallback. canonical은 SQLite, trace는 뷰용. |
| 4 | human-gate = `status='awaiting_*'` + 텔레그램 `/resume` | `interrupt()` 사용 금지. 상태를 DB에 영속화하고 외부에서 answer 주입 → 재개. |

---

## 2. 도메인 온톨로지 (엔티티 / 관계)

```
Album(기획)
  └─ Run               ← 파이프라인 1회 실행 (album_slug 단위)
       ├─ Step*        ← 노드별 실행 기록 (작사/프롬프트/생성/프리필터/후처리/영상/업로드)
       ├─ HumanTask*   ← 사람 개입 지점 (awaiting_selection 등), TTL(expires_at)
       └─ Artifact*    ← 산출물 메타 (경로 + sha256 only, bytes 저장 금지)
```

- **Run.status**: `pending → running → awaiting_{kind} → running → done | failed`
- **Step.status**: `pending → running → done | failed` (재시도는 attempt 증가)
- **HumanTask.status**: `open → answered | expired`
- 멱등성: 생성/업로드 노드는 idempotency key로 중복 산출(가짜 mp3 재발, D-004) 차단.

---

## 3. Phase 로드맵

| Phase | 내용 | 외부 의존성 | 상태 |
|-------|------|------------|------|
| 0 | 설계 확정 + 문서화(이 문서) | — | ✅ 완료 |
| **2** | **FSM 코어** (store/engine/idempotency/claude_cli/trace + 노드 stub + pytest) | **0 (키 불필요)** | **← 이번 작업** |
| 1 | Suno 서드파티 API PoC (generate 실연동) | Suno API 키 | ⏸ PM이 사용자에게 키 요청 중 |
| 3 | 노드 실구현 — 작사/프롬프트/프리필터(F01 역할 재정의) | Phase 1, 2 | 예정 |
| 4 | 후처리(-14 LUFS)/영상/unlisted 업로드 노드 | Phase 3 | 예정 |
| 5 | 텔레그램 통합 — 후보카드(F02) + `/resume` 핸들러 | Phase 3, 4 | 예정 |
| 6 | 하드닝 + LangSmith 모니터링 활성화 | LangSmith 키 | 예정 |

> Phase 3~6의 세부는 Phase 1/2 완료 후 재확정. 위는 제안 골격.

---

## 4. Phase 2 — FSM 코어 (이번 작업 상세)

새 모듈 `autopilot/` (외부 의존성 0).

### 4.1 SQLite 스키마 (`autopilot/store.py`)

| 테이블 | 컬럼 |
|--------|------|
| `runs` | id, album_slug, status, current_step, state_version, created_at, updated_at |
| `steps` | run_id, step_name, status, attempt, input_json, output_json, error_json, started_at, ended_at |
| `human_tasks` | id, run_id, kind, payload_json, status, answer_json, created_at, **expires_at**(TTL) |
| `artifacts` | id, run_id, step_name, kind, **path, sha256**, meta_json (← 경로+해시만, bytes 금지) |

### 4.2 데코레이터 (`autopilot/engine.py`)

- **`@step`**: 실행 전후 `steps` 기록 + trace 이벤트 emit + 실패 시 재시도(attempt) + 멱등키 체크.
  - **resume 시 `steps.status='done'`이면 skip** (side-effect 중복 방지 — codex 경고).
- **`@human_gate`**: `status='awaiting_{kind}'`로 정지 + `human_tasks` insert.
  재개는 외부에서 answer 주입 → 다음 step 진행.

### 4.3 부속 모듈

- **`autopilot/idempotency.py`**: 생성/업로드에 키 부여. 같은 키 재시도 시 중복 생성 차단(D-004).
- **`autopilot/claude_cli.py`**: `subprocess.run`으로 `npx @anthropic-ai/claude-code -p ... --tools "" --no-session-persistence`.
  exit_code/stderr/elapsed 로깅 + OAuth 만료 감지 훅(stderr auth 에러 패턴 → 명확한 예외).
- **`autopilot/trace.py`**: 노드 이벤트를 `trace.jsonl`에 기록(뷰용, canonical은 SQLite).
  LangSmith SDK 있으면 `@traceable` 미러, 없으면 no-op. **대용량 프롬프트는 경로+hash만. 종료 전 flush.**
- **`autopilot/nodes/generate.py`**: 인터페이스만 `generate(prompt, n=2) -> [candidate_paths]`,
  본문 `raise NotImplementedError("Phase 1 PoC에서 서드파티 API 연동")`.
  나머지 노드(작사/프롬프트/프리필터/후처리/업로드)도 시그니처 stub.

### 4.4 테스트 (pytest)

1. FSM 상태전이: run 생성 → step 진행 → done.
2. **재개**: 중간 step 실패 후 재실행 시 완료 step skip + 실패 step부터 재개.
3. **멱등성**: 같은 키 2회 호출 시 1회만 실행.
4. human_gate: awaiting 정지 + answer 주입 후 진행.
5. state_version 마이그레이션 훅 1개.

---

## 5. 하드닝 체크리스트 (3-way 리뷰에서 도출)

- [ ] **canonical state = SQLite 단일**. trace.jsonl은 절대 진실원이 아님(뷰용).
- [ ] **resume 멱등**: 완료 step 재실행 금지 → 업로드/생성 side-effect 중복 차단.
- [ ] **artifact는 경로+sha256만** 저장. bytes/객체 DB 저장 금지(용량 폭발 방지).
- [ ] **idempotency key**: 생성/업로드 작업 중복 차단(D-004 가짜 mp3 재발 방지).
- [ ] **human_task TTL(expires_at)**: 무한 대기 방지. 만료 시 expired 전이.
- [ ] **interrupt() 금지**: human-gate는 DB status + 외부 answer 주입 방식.
- [ ] **Claude CLI OAuth 만료 감지**: 장시간 대기 후 호출 시 stderr auth 패턴 → 명확한 예외.
- [ ] **CLI 버전 고정**: npx 최신 자동설치 금지(D-003). `@anthropic-ai/claude-code@<pin>`.
- [ ] **trace flush**: 프로세스 종료 전 trace.jsonl flush(이벤트 유실 방지).
- [ ] **LangSmith no-op fallback**: 키 없을 때 파이프라인 정상 작동.
- [ ] **단일 실행 보장**: 동시 batch 충돌 방지(D-004 Chrome 포트 경합 교훈) — run lock.

---

## 6. 관련 DIFFICULTY

- **D-001**: Suno hCaptcha → 자체 무인생성 불가 → 서드파티 API(결정 2).
- **D-003**: Claude CLI npx 최신 자동설치 silent outage → 버전 고정.
- **D-004**: 가짜 mp3 이동 + 동시 batch 충돌 → idempotency key + run lock.
- **D-005/D-007**: Suno v1/v2 폴링, 길이 제어 불가 → 노드 구현(Phase 3~4)에서 반영.
