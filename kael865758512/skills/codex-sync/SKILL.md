# Codex Sync

Use this skill to keep cross-device Codex progress synchronized through a shared markdown file in Git.

## Purpose
- Resume work across home/work machines without losing state.
- Keep one lightweight source of truth for current progress.
- Reduce repeated onboarding between Codex sessions.
- Make reading shared state mandatory before substantial work starts.
- Mirror Kael's shared skill and sync infrastructure between the team repo and the personal repo.

## Canonical File
- `CURRENT_STATE.md`

## Startup Workflow
Before substantial work:
1. Pull latest changes.
2. Read `CURRENT_STATE.md`.
3. Summarize current task, status, and next steps.
4. Continue only after the shared state is understood.

This startup read is mandatory when switching devices or starting a fresh Codex session.

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

## Mirroring Rule
Kael keeps shared skill and sync infrastructure in both places:
- team repo path: `kael865758512/skills/`
- personal repo path: `shared/agents/` inside `kael-openclaw-hub`

If a shared continuity rule, sync protocol, or reusable Codex workflow is updated, keep both repos aligned.

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
