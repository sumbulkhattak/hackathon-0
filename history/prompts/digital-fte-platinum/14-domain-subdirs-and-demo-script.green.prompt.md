---
id: 14
title: Domain subdirs and Platinum demo script
stage: green
date: 2026-02-18
surface: agent
model: claude-opus-4-6
feature: digital-fte-platinum
branch: feature/digital-fte-platinum-tier
user: human
command: implement domain subdirs and demo
labels: ["platinum", "domain-subdirs", "demo", "cloud-local", "claim-by-move"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/watchers/base_watcher.py
  - src/watchers/gmail_watcher.py
  - src/watchers/file_watcher.py
  - src/orchestrator.py
  - src/web.py
  - src/dashboard.py
  - setup_vault.py
  - demo_platinum.py
  - tests/test_integration.py
  - tests/test_demo_platinum.py
  - tests/watchers/test_file_watcher.py
  - skills/vault-sync.md
tests:
  - tests/test_demo_platinum.py (2 new: domain_subdirs_created, platinum_demo_flow)
  - tests/test_integration.py (6 updated for rglob)
  - tests/watchers/test_file_watcher.py (1 updated for domain path)
---

## Prompt

Do both step by step: 1) Implement domain-specific subdirectories (/Needs_Action/<domain>/, /Plans/<domain>/, /Pending_Approval/<domain>/), 2) Create Platinum demo script (end-to-end flow).

## Response snapshot

Implemented domain-specific subdirectories: BaseWatcher now accepts domain parameter, GmailWatcher uses domain="email", FileWatcher uses domain="file". Orchestrator derives domain from file path and writes plans/approvals to domain subdirs. Web dashboard scans recursively with rglob, approve/reject routes support path parameters. setup_vault creates email/file/social subdirs. Created demo_platinum.py that simulates the full Platinum demo gate: email arrives → cloud drafts → approval file → cloud writes update signal → local merges updates → user approves → local executes send → logs → moves to Done. All 294 tests pass.

## Outcome

- Impact: Closes the last major Platinum code gap; demo script proves the full cloud/local split flow
- Tests: 294 passing (2 new + 7 updated)
- Files: 12 files created/modified
- Next prompts: Commit changes, create PR, record demo video
- Reflection: The domain subdir change required updating integration tests from glob to rglob. The demo script provides a clear, runnable proof of the Platinum tier flow.

## Evaluation notes (flywheel)

- Failure modes observed: 7 integration test failures from glob→rglob change (expected, fixed immediately)
- Graders run and results (PASS/FAIL): 294 tests PASS, 0 FAIL; demo script PASS; all 6 HTTP endpoints PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Run demo with --manual flag to test web UI approval flow
