---
name: slack-send
description: Send a Slack message to a teammate or channel using a theme/persona. Part of the slack plugin. Use when the user wants to send a Slack message, notify someone, or communicate with the team.
version: 1.0.0
---

# Slack Send

Send a Slack message with persona-driven tone selection and repo-based recipient lookup.

## Hard Constraints

- NEVER send a message without first showing the draft preview and receiving explicit `yes` confirmation.
- NEVER fabricate teammate names or Slack IDs — only use data from config.json.
- NEVER modify config.json using Write — use Edit to patch specific fields so the rest of the file is preserved.

## Paths

- Config: `/Users/oren/.claude/plugins/cache/oren-pinkas/slack/1.0.0/config.json`
- Themes dir: `/Users/oren/.claude/plugins/cache/oren-pinkas/slack/1.0.0/themes/`

## Flow

### Step 1 — Load config

Read `/Users/oren/.claude/plugins/cache/oren-pinkas/slack/1.0.0/config.json`.

Extract:
- `team` — array of `{ name, slack_id }` objects (the people you can message)
- `repos` — array of `{ repo, default_recipients, default_channel }` mappings

### Step 2 — Detect current repo

Run:
```bash
git remote get-url origin 2>/dev/null
```

Parse the repo short name:
- SSH URL `git@github.com:org/repo-name.git` → `repo-name`
- HTTPS URL `https://github.com/org/repo-name.git` → `repo-name`
- Take the final path segment and strip `.git`

If the command fails or returns empty, repo detection is unavailable — proceed without it.

### Step 3 — Resolve recipient

Apply this priority order:

1. **Explicit user override**: if the user named a specific person or channel in their request, use that. Look up the person by name in `team[]` to get their `slack_id`.
2. **Repo mapping**: if a repo was detected and `repos[]` contains an entry where `repo` matches the detected repo name:
   - If `default_channel` is set (non-null), use it as the destination channel.
   - Else if `default_recipients` is set and non-empty, use those Slack IDs as recipients.
3. **Ask the user**: if neither override nor mapping resolved a recipient, list team members by name and ask who to send to.

If the repo was detected but has no mapping in `repos[]`, continue to send — but after a successful send, offer to save the chosen recipient to config (see "Saving recipient to config" below).

If the user specifies a Slack channel name (e.g., `#engineering`), use it as the `channel_id` directly. For DMs, use the recipient's Slack user ID as the `channel_id`.

When sending to multiple `default_recipients`, send a separate message to each.

### Step 4 — Resolve theme

Apply this priority order:

1. **User-specified theme name**: if the user names a theme (single token), check whether `themes/{name}.md` exists on disk. If the file exists, read it and use its persona rules. If the file does not exist, tell the user and fall back to `straight`.
2. **User-specified freetext persona**: if the user provided a multi-word description (not a single filename token), treat the entire description as an inline persona — apply it directly without loading any file.
3. **Default**: if the user specified nothing, use the `straight` theme. Read `themes/straight.md` if it exists; otherwise apply "no persona, no flair — just the facts" literally.

### Step 5 — Compose draft message

Write the message applying the resolved theme's persona rules to the user's intent. Keep the message natural and appropriately concise for a Slack message.

### Step 6 — Show confirm-before-send preview

Display exactly this format (use the box-drawing characters as shown):

```
📨 Draft message:
──────────────────
[full message text]
──────────────────
To: [Name] ([Slack ID])   ← use channel name if sending to a channel
Theme: [theme name or "inline persona"]

Send? [yes / edit / cancel]
```

Wait for the user's response.

### Step 7 — Handle confirmation response

- **`yes`**: proceed to Step 8 (send).
- **`edit`**: ask the user what to change (e.g., "What would you like to change?"). Apply the requested changes, redraft the message, and go back to Step 6 to show the updated preview. Repeat this loop — do NOT send until you receive an explicit `yes`.
- **`cancel`**: abort. Respond: "Message cancelled. Nothing was sent."
- Any other response: treat as `edit` — ask for clarification.

### Step 8 — Send the message

Call `mcp__claude_ai_Slack__slack_send_message` with:
- `channel_id`: the resolved Slack user ID (for DMs) or channel ID/name
- `text`: the composed message

If sending to multiple recipients, call the tool once per recipient.

### Step 9 — Return result

Surface the message permalink or timestamp from the tool's response. If the tool returns no link, report: "Sent to [Name/channel] successfully." and include whatever channel/timestamp info is available.

---

## Saving Recipient to Config

If the repo was detected but had no mapping, and a message was sent successfully, ask:

> "Want me to save [Name] as the default recipient for `[repo-name]`? I'll update config.json."

If the user says yes, use the Edit tool to append a new object to the `repos` array in config.json:
```json
{ "repo": "<repo-name>", "default_recipients": ["<slack_id>"], "default_channel": null }
```

Patch only the `repos` array — do not rewrite the whole file.

---

## Side Requests

- **"Add a new theme"**: write a new `.md` file to `/Users/oren/.claude/plugins/cache/oren-pinkas/slack/1.0.0/themes/{name}.md` describing the persona rules. Confirm the theme name and description with the user first.
- **"Add a teammate"**: ask for the person's name and Slack ID, then use the Edit tool to append a new entry to `team[]` in config.json.
