---
id: 12
title: Extract hackathon tier requirements from PDF
stage: misc
date: 2026-02-17
surface: agent
model: claude-opus-4-6
feature: digital-fte-platinum
branch: feature/digital-fte-platinum
user: human
command: read and extract
labels: ["hackathon", "requirements", "tiers", "bronze", "silver", "gold", "platinum"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - history/prompts/digital-fte-platinum/12-extract-hackathon-tier-requirements.misc.prompt.md
tests:
  - none
---

## Prompt

Read the hackathon PDF document at "C:\Users\LAPTOP WORLD\Downloads\Personal AI Employee Hackathon 0- Building Autonomous FTEs in 2026.pdf" and extract ALL tier requirements in detail. For each tier (Bronze, Silver, Gold, Platinum), list every specific requirement, feature, and deliverable mentioned. Be extremely thorough - don't miss any detail. Return the full structured breakdown.

## Response snapshot

Extracted all four tier requirements (Bronze, Silver, Gold, Platinum) from the 29-page hackathon PDF. Bronze (8-12h): Obsidian vault with Dashboard.md/Company_Handbook.md, one watcher, Claude Code vault integration, folder structure, Agent Skills. Silver (20-30h): adds 2+ watchers, LinkedIn posting, Plan.md reasoning loop, 1 MCP server, HITL approval, scheduling, Agent Skills. Gold (40+h): adds cross-domain integration, Odoo Community accounting via JSON-RPC MCP, Facebook/Instagram/Twitter integration, multiple MCP servers, weekly CEO briefing, error recovery, audit logging, Ralph Wiggum loop, documentation, Agent Skills. Platinum (60+h): adds 24/7 cloud deployment, work-zone specialization (cloud=drafts, local=approvals+actions), synced vault delegation with claim-by-move and single-writer rules, secrets isolation, cloud Odoo with HTTPS/backups, optional A2A upgrade, and a minimum passing demo gate (email arrives while local offline -> cloud drafts -> local approves -> send -> log -> done).

## Outcome

- Impact: Full understanding of all hackathon deliverables across 4 tiers for project planning
- Tests: none
- Files: PHR created
- Next prompts: Compare current implementation against tier requirements; identify gaps; plan remaining work
- Reflection: The PDF is comprehensive at 29 pages. Platinum tier has the most nuanced requirements including cloud/local split, vault sync protocols, and a specific demo passing gate.

## Evaluation notes (flywheel)

- Failure modes observed: PDF rendering required pymupdf fallback due to missing pdftoppm; encoding required utf-8 reconfiguration
- Graders run and results (PASS/FAIL): N/A - information extraction task
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
