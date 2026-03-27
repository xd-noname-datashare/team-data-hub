# Codex Sync

Use this skill to keep cross-device Codex progress synchronized through a shared markdown file in Git.

## Purpose
- Resume work across home/work machines without losing state.
- Keep one lightweight source of truth for current progress.
- Reduce repeated onboarding between Codex sessions.

## Canonical File
- `CURRENT_STATE.md`

## Startup Workflow
Before substantial work:
1. Pull latest changes.
2. Read `CURRENT_STATE.md`.
3. Summarize current task, status, and next steps.
4. Continue only after the shared state is understood.

## Update Workflow
Update `CURRENT_STATE.md` when:
- a new task starts
- a milestone completes
- a blocker appears
- a decision changes the plan
- a session ends before completion

## Write Rules
- Prefer short append-only notes in `Activity Log`.
- Refresh summary sections if stale.
- Use timestamps with timezone.
- Keep content factual and compact.

## Privacy Rules
Safe to record:
- current task
- completed milestones
- blockers
- next steps
- file paths
- repo names

Do not record:
- passwords
- API keys
- tokens
- cookies
- personal private conversations
- raw secrets copied from terminals

## Recommended Git Commands
```bash
git pull
```

Update the file, then:

```bash
git add kael865758512/skills/codex-sync/
git commit -m "docs: update codex shared state"
git push
```

