# Skill: Social Media Integration

## Description
Post content to LinkedIn, Facebook, and Twitter/X. Supports direct posting (with API credentials) and draft-only mode (creates approval files for human review before publishing).

## Trigger
- User requests a social media post
- Orchestrator generates social content from email summaries or briefings
- Scheduled social media updates

## Supported Platforms

### LinkedIn
- Full text posts via LinkedIn API
- Requires `LINKEDIN_ACCESS_TOKEN` in `.env`

### Facebook
- Page posts via Graph API
- Requires `FACEBOOK_PAGE_TOKEN` in `.env`

### Twitter/X
- Tweets with automatic 280-character truncation
- Requires `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` in `.env`

## Draft Mode (HITL)
When credentials are not configured or when human review is desired, use `create_draft_post` to create a markdown file in `vault/Pending_Approval/` with:
- Platform target
- Post content
- Approval/rejection workflow (move to Approved/ or Rejected/)

## MCP Server Tools

| Tool | Description |
|------|-------------|
| `post_to_linkedin(content)` | Post directly to LinkedIn |
| `post_to_facebook(content)` | Post directly to Facebook |
| `post_to_twitter(content)` | Post to Twitter (280 char limit) |
| `create_draft_post(platform, content)` | Create draft for human review |
| `get_social_summary()` | Summary of posting activity (7 days) |

## Input
```yaml
platform: linkedin | facebook | twitter
content: "Post text content here"
```

## Output
```json
{
  "success": true,
  "platform": "linkedin",
  "content": "Post text content here"
}
```

## Implementation
- Module: `src/social.py` (LinkedInPoster, FacebookPoster, TwitterPoster)
- MCP Server: `mcp_servers/social_server.py`
- Config: Social media API tokens in `.env`
- Logs: Actions logged to `vault/Logs/` as `social_posted` entries

## Error Handling
- Missing credentials return `{"success": false, "error": "... not configured"}`
- Twitter content exceeding 280 characters is automatically truncated with "..."
- Draft creation failures are caught and returned as structured errors
