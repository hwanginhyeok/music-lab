# Dispatch Protocol (coordination board)

> Source of truth for pane-to-pane work in this project. The board markdown under
> `coordination/board/messages/*.md` is authoritative — not chat scrollback, not a
> tmux keystroke. Every pane reads the board before starting delegated work and
> replies **in the same thread**.

## Tooling

```bash
BOARD=~/hih-skills/hih-handoff/scripts/board.py
python3 "$BOARD" --project . init
python3 "$BOARD" --project . post --from pm --to claude --kind dispatch \
  --title "..." --task-id T-XXX --done-signal "..." --body "..."
python3 "$BOARD" --project . list --as claude
python3 "$BOARD" --project . reply --from claude --status completed <msg.md>
python3 "$BOARD" --project . close --from pm <msg.md>
```

## Message metadata contract

Every dispatch/reply carries these fields (board.py stores the core set in
frontmatter; the rest go in the message body header when relevant):

| field | meaning |
|-------|---------|
| `from` | sender role/person (pm, codex, claude, glm, pm-worker, user) |
| `to` | recipient(s): `all`, `pm`, `codex`, `claude`, `glm`, or comma list |
| `session` | target tmux session name (bea, luck-turtle, insung, PM, ...) |
| `window` | target window index |
| `pane` | target pane index (the executor pane) |
| `model` | model expected to act (opus, sonnet, gpt-5.x/codex, glm-5.x) |
| `role` | executor role marker (`@hih_role`: role=claude, role=codex, role=glm, role=pm-worker) |
| `kind` | dispatch, review, debate, question, notice, reply |
| `status` | open, answered, partial, blocked, question, closed |
| `thread_id` | board message id the reply belongs to (same-thread rule) |
| `source_task` | originating task/PLAN id (e.g. PM-121, LT-80) |
| `reply_expected` | yes/no — does the sender block on an ACK/deliverable |
| `done_signal` | testable completion condition (passing test, file exists, curl==X) |
| `evidence_path` | path to the deliverable/verification evidence (log, diff, run dir) |

## Rules

1. **Board md is the source of truth.** Decisions, dispatches, and completion live
   in `messages/*.md`, not in chat memory or a raw tmux keystroke.
2. **tmux send-keys only points to the board.** A keystroke to a pane may carry
   *only* a pointer to the board message (its path/id) — never the work payload
   itself. The pane opens the board file to get the real instruction.
3. **Reply in the same thread.** The executor appends its reply to the same
   message (`reply --from <role> --status ...`). No side-channel "done" in chat.
4. **Pane 4 / reserved does not execute.** A pane marked reserved/no-exec
   (`role=reserved` / pane 4 in the codex+claude+glm layout) is a scratch/observer
   slot — it never runs delegated work.
5. **PM closes only after deliverable verification.** A thread is closed
   (`close --from pm`) only once PM has inspected the `evidence_path` (diff/test/
   artifact), not on a bare "완료" reply. Unverifiable → keep open + record why.
6. **Real evidence or explicit skip.** Multi-model dispatch (Codex/GLM/Claude
   legs) must produce provider artifacts or board replies. If a provider/pane is
   unavailable, the thread is marked `blocked` with the exact failing
   session/pane/provider — never synthesized as if the leg ran.

## Reachability

Panes on unreachable hosts (e.g. `/home/gint_pcd/*` from a `/home/window11`
machine) cannot be driven from here. Dispatches to them are recorded as
`blocked: unreachable-host` with the target path, not silently dropped.
