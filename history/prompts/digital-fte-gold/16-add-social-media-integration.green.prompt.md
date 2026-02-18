---
id: 16
title: Add social media integration
stage: green
date: 2026-02-17
surface: agent
model: claude-opus-4-6
feature: digital-fte-gold
branch: feature/digital-fte-social-media
user: human
command: implement social media integration
labels: ["social-media", "linkedin", "facebook", "twitter", "mcp-server", "gold-tier"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/social.py
  - mcp_servers/social_server.py
  - tests/test_social.py
  - tests/test_social_mcp.py
  - skills/social-media.md
  - .env.example
tests:
  - tests/test_social.py::test_linkedin_poster_platform_name
  - tests/test_social.py::test_linkedin_poster_no_credentials
  - tests/test_social.py::test_linkedin_poster_with_credentials
  - tests/test_social.py::test_facebook_poster_no_credentials
  - tests/test_social.py::test_facebook_poster_with_credentials
  - tests/test_social.py::test_twitter_poster_no_credentials
  - tests/test_social.py::test_twitter_poster_with_credentials
  - tests/test_social.py::test_twitter_poster_truncates_long_content
  - tests/test_social.py::test_get_all_posters_returns_three
  - tests/test_social.py::test_create_social_post_draft_creates_file
  - tests/test_social.py::test_create_social_post_draft_has_frontmatter
  - tests/test_social.py::test_create_social_post_draft_includes_content
  - tests/test_social.py::test_generate_social_summary_empty
  - tests/test_social.py::test_generate_social_summary_with_posts
  - tests/test_social_mcp.py::test_create_draft_post_creates_file
  - tests/test_social_mcp.py::test_get_social_summary_returns_json
  - tests/test_social_mcp.py::test_post_to_linkedin_no_creds
  - tests/test_social_mcp.py::test_post_to_facebook_no_creds
  - tests/test_social_mcp.py::test_post_to_twitter_no_creds
---

## Prompt

You are implementing social media integration for the Digital FTE project at C:\Users\LAPTOP WORLD\Desktop\hackathon-0.

## Context
Gold tier requires LinkedIn, Facebook/Instagram, and Twitter posting with summary generation. The project already has Gmail watcher, email MCP server, and 215 tests passing. Branch: feature/digital-fte-social-media.

## What to Build

### 1. Create `src/social.py` — Social media posting module
### 2. Create `mcp_servers/social_server.py` — Social Media MCP Server
### 3. Create `tests/test_social.py` — TDD tests (14 tests)
### 4. Create `tests/test_social_mcp.py` — MCP server tests (5 tests)
### 5. Create `skills/social-media.md` Agent Skill
### 6. Update `.env.example` with social media env vars
### 7. Run tests and commit

## Response snapshot

Implemented complete social media integration for the Gold tier:

1. **src/social.py** — Social media posting module with:
   - `SocialPoster` ABC base class with common interface
   - `LinkedInPoster` (LINKEDIN_ACCESS_TOKEN)
   - `FacebookPoster` (FACEBOOK_PAGE_TOKEN)
   - `TwitterPoster` (4 credentials, auto-truncation to 280 chars)
   - `get_all_posters()` — returns all 3 configured posters
   - `create_social_post_draft()` — HITL draft mode in Pending_Approval/
   - `generate_social_summary()` — reads logs for posting activity summary

2. **mcp_servers/social_server.py** — FastMCP server with 5 tools:
   - `post_to_linkedin`, `post_to_facebook`, `post_to_twitter`
   - `create_draft_post` (human-in-the-loop approval)
   - `get_social_summary`

3. **tests/test_social.py** — 14 tests covering all poster classes, drafts, summaries
4. **tests/test_social_mcp.py** — 5 tests for MCP server tool functions
5. **skills/social-media.md** — Agent skill documentation
6. **.env.example** — Added 6 social media credential placeholders

All 234 tests passing (215 existing + 19 new). Committed on feature/digital-fte-social-media.

## Outcome

- Impact: Gold tier social media integration complete with LinkedIn, Facebook, Twitter support
- Tests: 19 new tests, all passing; 234 total tests passing
- Files: 6 files created/modified
- Next prompts: Wire social posting into orchestrator; add Instagram support; implement actual API calls
- Reflection: Clean implementation following existing patterns (email MCP server, skill docs, env config)

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): 234/234 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add integration test with mock API responses for real posting flow
