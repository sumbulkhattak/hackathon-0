---
id: 15
title: Upgrade Dashboard to Jinja2 Templates
stage: green
date: 2026-02-18
surface: agent
model: claude-opus-4-6
feature: digital-fte-platinum
branch: feature/digital-fte-platinum-tier
user: human
command: implement
labels: ["jinja2", "templates", "dashboard", "refactor"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - templates/base.html
  - templates/dashboard.html
  - templates/view.html
  - static/css/style.css
  - src/web.py
tests:
  - tests/test_web.py
---

## Prompt

Implement the following plan:

# Plan: Upgrade Dashboard to Jinja2 Templates

## Context
The current `src/web.py` renders HTML via inline Python f-strings (~160 lines of CSS + ~160 lines of HTML building). Jinja2 is already in `requirements.txt` but unused. The user wants proper HTML template files with separated CSS for a cleaner, more maintainable dashboard.

## Approach

### 1. Create directory structure
- `templates/` — Jinja2 HTML files
- `templates/base.html` — Shared layout (head, CSS, header, footer)
- `templates/dashboard.html` — Main dashboard (extends base)
- `templates/view.html` — File viewer page (extends base)
- `static/css/style.css` — Extracted CSS from `_css()` function

### 2-6. Create templates, extract CSS, update web.py with Jinja2Templates and StaticFiles, add /tasks endpoint, remove inline rendering functions.

## Response snapshot

Implemented the full Jinja2 template upgrade:
- Created `templates/base.html` (shared layout with CSS link and content block)
- Created `templates/dashboard.html` (extends base, all dashboard sections preserved)
- Created `templates/view.html` (extends base, file viewer with back link)
- Created `static/css/style.css` (all CSS extracted from `_css()`)
- Updated `src/web.py`: replaced `_render_dashboard()` and `_css()` with `Jinja2Templates` + `StaticFiles`, added `/tasks` JSON endpoint, used modern `TemplateResponse(request, name, context)` signature
- All 24 web tests and 294 total tests pass with zero new warnings

## Outcome

- ✅ Impact: Dashboard now uses proper Jinja2 templates with separated CSS, improving maintainability and enabling future template reuse
- 🧪 Tests: 24/24 web tests pass, 294/294 full suite pass, zero deprecation warnings
- 📁 Files: 4 created (templates/base.html, templates/dashboard.html, templates/view.html, static/css/style.css), 1 modified (src/web.py)
- 🔁 Next prompts: Add more template pages, template partials for reusable components, static asset caching
- 🧠 Reflection: Clean separation achieved. Using modern TemplateResponse signature avoided deprecation warnings.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): pytest PASS (294/294)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add Jinja2 template partials for approval items and activity entries
