# Skill: Vault Sync (Cloud/Local Split Deployment)

## Description
Git-based vault synchronization for cloud/local split deployment. Implements claim-by-move protocol where cloud zone creates drafts and local zone claims items for execution.

## Trigger
- Periodic sync cycle (every 60 seconds in continuous mode)
- Manual sync before/after processing cycles
- On startup to pull latest vault state

## Protocol: Claim-by-Move
1. **Cloud zone** polls Gmail, runs Claude, writes drafts to `Pending_Approval/`
2. **Cloud zone** commits and pushes via `push_vault()`
3. **Local zone** pulls via `pull_vault()`, sees new items
4. **Local zone** claims items by moving to `Approved/` or `Rejected/` via `claim_item()`
5. **Local zone** pushes the claim back so cloud sees it

### In_Progress/<agent>/ — Preventing Double-Work
- First agent to move an item from `Needs_Action/` to `In_Progress/<agent>/` owns it
- Other agents must check all `In_Progress/*/` subdirectories before claiming
- Use `claim_to_in_progress(vault, filename, agent_name)` to claim atomically
- After processing, move from `In_Progress/<agent>/` to `Pending_Approval/` or `Done/`

### Updates/ — Cloud-to-Local Dashboard Signals
- **Cloud zone** writes status updates to `Updates/` (never writes Dashboard.md directly)
- **Local zone** runs `merge_updates()` to fold `Updates/` files into Dashboard.md
- After merging, update files are removed from `Updates/`
- This enforces the **single-writer rule** for Dashboard.md (Local only)

### Single-Writer Rules
- Only cloud writes to `Pending_Approval/` (new drafts) and `Updates/` (signals)
- Only local writes to `Approved/`, `Rejected/`, `Done/`, `Dashboard.md`
- Both can read any folder
- Conflicts resolved by git rebase on pull

## Work Zones
| Capability | Cloud | Local |
|-----------|-------|-------|
| Read email | Yes | Yes |
| Draft plans | Yes | Yes |
| Send email | No | Yes |
| Execute actions | No | Yes |
| Approve/Reject | No | Yes |
| Social media | No | Yes |
| Odoo operations | No | Yes |

## Implementation
- Module: `src/vault_sync.py`
  - `init_sync()` — initialize git repo in vault
  - `push_vault()` — commit and push changes
  - `pull_vault()` — pull remote changes
  - `sync_vault()` — full pull+push cycle
  - `claim_item()` — move file between folders
  - `claim_to_in_progress()` — claim to In_Progress/<agent>/
  - `write_update()` — cloud writes update signal
  - `merge_updates()` — local merges Updates/ into Dashboard.md
  - `get_sync_status()` — repo status report
- Module: `src/secrets_isolation.py`
  - `validate_credentials()` — check zone-appropriate credentials
  - `get_zone_capabilities()` — runtime capability matrix
- Config: `WORK_ZONE=cloud|local` in `.env`
- Tests: `tests/test_vault_sync.py` (22 tests), `tests/test_secrets_isolation.py` (9 tests)
