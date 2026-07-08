# Coordination Board

Single shared board for pane-to-pane work messages.

Every pane checks `messages/*.md` before starting new work.

Frontmatter contract:

- `from`: sender role/person
- `to`: `all`, `pm`, `codex`, `claude`, `glm`, or comma-separated roles
- `kind`: dispatch, review, debate, question, notice, reply
- `status`: open, answered, partial, blocked, question, closed

Rules:

- `to: all` means every pane should inspect and reply when relevant.
- Targeted messages are acted on only by matching recipients.
- Replies are appended to the same message under `## Replies`.
- PM closes the thread when deliverable/evidence is verified.
