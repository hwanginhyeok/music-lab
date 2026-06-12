# LLM Workflow Rules (be-a-studio)

## Core: Opus does not touch code

Code analysis/writing/modification/refactoring — all delegated to GLM.
Opus only directs + reviews + reports to the user.

## GLM delegation targets (no exceptions)

- Writing/modifying code
- Code analysis (reading files and grasping structure)
- Test generation
- Refactoring
- Debugging (simple errors)

## What Opus does

- Conversing with the user
- Task planning/design
- Writing GLM instruction prompts
- Reviewing GLM results → reporting to the user
- Re-directing when results fall short (no direct modification)
- Writing documents (md)

## How to call GLM

```bash
python3 ~/project-manager/scripts/glm_client.py \
    --prompt "분석할 내용" \
    --project be-a-studio \
    --feature 기능명
```

## On violation

If Opus directly analyzes code with Grep/Read, or modifies code with Edit/Write, that is an **architecture violation**.
Always go through glm_client.py.
