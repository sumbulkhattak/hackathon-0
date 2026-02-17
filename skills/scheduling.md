# Skill: Task Scheduling

## Description
Run the Digital FTE on a schedule using cron (Linux/Mac) or Windows Task Scheduler.

## Modes

### Continuous Mode (default)
```bash
python main.py
```
Runs in a loop, polling Gmail every N seconds. Web dashboard runs alongside.

### One-Shot Mode (for cron/Task Scheduler)
```bash
python -m src.scheduler --once
```
Runs one full cycle (check Gmail → process actions → execute approved → review rejected → update dashboard) and exits.

### Dashboard-Only Mode
```bash
python main.py --dashboard-only
```
Starts the web dashboard without Gmail. Useful for monitoring vault state.

## Scheduling with Cron (Linux/Mac)

Add to crontab (`crontab -e`):
```cron
# Run Digital FTE every 5 minutes
*/5 * * * * cd /path/to/hackathon-0 && python -m src.scheduler --once >> /tmp/digital-fte.log 2>&1
```

## Scheduling with Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task → Name: "Digital FTE"
3. Trigger: Daily, repeat every 5 minutes
4. Action: Start a Program
   - Program: `python`
   - Arguments: `-m src.scheduler --once`
   - Start in: `C:\path\to\hackathon-0`

Or import the XML:
```bash
python -c "from src.scheduler import generate_task_scheduler_xml; print(generate_task_scheduler_xml())"
```

## Implementation
- Module: `src/scheduler.py` → `run_once()`, `generate_cron_entry()`, `generate_task_scheduler_xml()`
