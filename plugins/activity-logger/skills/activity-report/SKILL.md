---
name: activity-report
description: "Compile activity reports from Claude Code session logs, scoped to a target stakeholder. Supports date ranges and audience presets (technical, product, executive) or freeform audience descriptions."
---

# Activity Report Generator

Generate a stakeholder-scoped report from your Claude Code session activity logs.

## Invocation

This skill accepts optional arguments. Parse the user's input to extract:
- **Date range**: explicit (`2026-04-14..2026-04-19`) or shorthand (`today`, `yesterday`, `this-week`, `last-week`, `this-month`)
- **Stakeholder**: `--for <preset-or-description>` where preset is one of `technical`, `product`, `executive`

If arguments are missing, ask the user interactively:
1. "What date range? (e.g., `today`, `last-week`, `2026-04-14..2026-04-19`)"
2. "Who is the audience? (e.g., `technical`, `product`, `executive`, or describe them)"

## Steps

### 1. Compile session data

Run the compile-sessions script to gather, deduplicate, and group all session logs:

```bash
/usr/bin/python3 "<plugin-root>/scripts/compile-sessions.py" <date-range-arg>
```

Where `<plugin-root>` is the directory two levels up from this skill file, and `<date-range-arg>` is the resolved date shorthand or explicit range (e.g., `today`, `this-week`, `2026-04-14..2026-04-19`).

The script outputs JSON with this structure:
```json
{
  "date_range": {"start": "2026-04-20", "end": "2026-04-20"},
  "stats": {"total_sessions": 129, "unique_sessions": 124, "duplicates_removed": 5, "projects": ["proj-a"]},
  "projects": {
    "proj-a": {
      "sessions": [{"session_id": "...", "date": "...", "processed": true, "narrative": "...", ...}],
      "totals": {"files_changed": 10, "insertions": 200, "deletions": 50}
    }
  }
}
```

If the script reports 0 unique sessions, tell the user: "No session logs found for {date range}. Sessions are logged automatically when you end a Claude Code session."

### 2. Load the stakeholder preset

If the `--for` value matches a preset name, read the corresponding file:
- `technical` → read `presets/technical.md` from this skill's directory
- `product` → read `presets/product.md` from this skill's directory
- `executive` → read `presets/executive.md` from this skill's directory

If the value doesn't match a preset, treat it as a freeform audience description and use it directly in the prompt.

### 3. Generate the report

Using the JSON data from step 1 and the tone guidance from step 2, generate the report as markdown.

The report should follow this structure:
```
# Activity Report: {date range description}

{Per-project sections with relevant detail per stakeholder type}

## Summary
{Aggregate stats: session count, project count, PRs, key themes}
```

Use the `stats` field to report dedup information when duplicates were removed.

### 4. Deliver the report

After generating the report, ask the user how they'd like to receive it (unless already specified in the invocation):

1. **Message** — display it in the conversation (default)
2. **Save to file** — ask where, suggest default: `~/claude-activity-log/reports/{date-range}-{stakeholder}.md`
3. **Post to Slack** — ask which channel or DM, then send via `mcp__claude_ai_Slack__slack_send_message`
4. **Other** — wait for further instructions

Multiple delivery options can be combined (e.g., save to file AND post to Slack).

When the user specifies delivery upfront (e.g., "save to ~/reports/weekly.md" or "send to #engineering"), skip the interactive prompt and execute directly.

### 5. Handle edge cases

- **Unprocessed summaries** (`processed: false`): include them with a note "(raw data — automated summary unavailable)"
- **Mixed projects**: always group by project, even if there's only one
- **Large result sets**: the script handles dedup; focus LLM effort on synthesis and tone
