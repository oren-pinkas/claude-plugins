---
name: slack-pr
description: Send a PR review request via Slack. Infers the PR from conversation context, looks up default recipient from config, composes a message with the chosen theme. Use when the user wants to request a PR review over Slack.
version: 1.0.0
---

# Slack PR

Send a PR review request via Slack with auto-inferred PR details, repo-based recipient lookup, and persona-driven tone.

## Hard Constraints

- NEVER call `gh` CLI or any external tool to look up PR details. Infer everything from conversation context only.
- NEVER send a message without first showing the draft preview and receiving explicit `yes` confirmation.
- NEVER fabricate PR details — if context is insufficient, ask the user.
- NEVER modify config.json using Write — use Edit to patch specific fields so the rest of the file is preserved.

## Paths

- Config: `/Users/oren/.claude/plugins/cache/oren-pinkas/slack/1.0.0/config.json`
- Themes dir: `/Users/oren/.claude/plugins/cache/oren-pinkas/slack/1.0.0/themes/`

## Flow

### Step 1 — Infer PR from conversation context

Scan the current conversation for any of the following signals (in priority order):

1. A GitHub PR URL (e.g., `https://github.com/org/repo/pull/123`) — extract the URL, repo name, and PR number.
2. A PR number mentioned explicitly (e.g., "PR #42", "pull request 42").
3. A PR title the user described or pasted.
4. A branch name the user mentioned that looks like a feature branch.

Do NOT call `gh`, `git`, or any CLI tool to resolve PR details. Work only with what is already present in the conversation.

If no PR can be inferred from any of these signals, ask the user:

> "Which PR should I send for review? (paste the URL or describe it)"

Wait for the user's answer before continuing.

### Step 2 — Load config

Read `/Users/oren/.claude/plugins/cache/oren-pinkas/slack/1.0.0/config.json`.

Extract:
- `team` — array of `{ name, slack_id }` objects
- `repos` — array of `{ repo, default_recipients, default_channel }` mappings

### Step 3 — Detect current repo

Run:
```bash
git remote get-url origin 2>/dev/null
```

Parse the repo short name:
- SSH URL `git@github.com:org/repo-name.git` → `repo-name`
- HTTPS URL `https://github.com/org/repo-name.git` → `repo-name`
- Take the final path segment and strip `.git`

If a PR URL was found in Step 1 and contains a repo name, use that repo name instead of (or to cross-check) the git remote result.

If the command fails or returns empty, repo detection is unavailable — proceed without it.

### Step 4 — Resolve recipient

Apply this priority order:

1. **Explicit user override**: if the user named a specific person in their request (e.g., "send to Tomer"), look them up in `team[]` by name to get their `slack_id`.
2. **Repo mapping**: if a repo was detected and `repos[]` contains a matching entry:
   - If `default_channel` is set (non-null), use it as the destination channel.
   - Else if `default_recipients` is set and non-empty, use those Slack IDs as recipients.
3. **Ask the user**: if neither override nor mapping resolved a recipient, list team members by name and ask who should review the PR.

If the repo has no mapping in `repos[]`, continue — but after a successful send, offer to save the recipient to config (see "Saving recipient to config" below).

For DMs, use the recipient's Slack user ID as the `channel_id`. When sending to multiple `default_recipients`, send a separate message to each.

### Step 5 — Resolve theme

Apply this priority order:

1. **User-specified theme name**: if the user names a theme (single token), check whether `themes/{name}.md` exists on disk. If it exists, read it and apply its persona rules. If it does not exist, tell the user and fall back to `straight`.
2. **User-specified freetext persona**: if the user provided a multi-word description, treat the entire description as an inline persona — apply it directly without loading any file.
3. **Default**: use the `straight` theme. Read `themes/straight.md` if it exists; otherwise apply "no persona, no flair — just the facts" literally.

### Step 6 — Compose review request message

Build the message in this structure, then apply the resolved theme persona over it:

1. **PR link** — the full GitHub URL (if available), or the PR identifier if no URL was found.
2. **2–3 bullet summary** — what the PR does. Infer from:
   - The PR title
   - The branch name (e.g., `feat/add-notification-bell` → "adds notification bell feature")
   - Any description the user provided in conversation

   If there is genuinely not enough context to write honest bullets, write one bullet summarizing what is known and add a placeholder: "_(add more context if needed)_". Do NOT invent details.

3. **Polite ask for review** — a brief, natural-sounding sentence asking the recipient to review.

Apply the theme persona over this structure — the persona shapes tone and word choice, not the content structure itself.

### Step 7 — Show confirm-before-send preview

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

### Step 8 — Handle confirmation response

- **`yes`**: proceed to Step 9 (send).
- **`edit`**: ask the user what to change (e.g., "What would you like to change?"). Apply the requested changes, redraft the message, and go back to Step 7 to show the updated preview. Repeat this loop — do NOT send until you receive an explicit `yes`.
- **`cancel`**: abort. Respond: "Message cancelled. Nothing was sent."
- Any other response: treat as `edit` — ask for clarification.

### Step 9 — Send the message

Call `mcp__claude_ai_Slack__slack_send_message` with:
- `channel_id`: the resolved Slack user ID (for DMs) or channel ID/name
- `text`: the composed message

If sending to multiple recipients, call the tool once per recipient.

### Step 10 — Return result

Surface the message permalink or timestamp from the tool's response. If the tool returns no link, report: "Sent to [Name/channel] successfully." and include whatever channel/timestamp info is available.

---

## Saving Recipient to Config

If the repo was detected but had no mapping, and a message was sent successfully, ask:

> "Want me to save [Name] as the default reviewer for `[repo-name]`? I'll update config.json."

If the user says yes, use the Edit tool to append a new object to the `repos` array in config.json:
```json
{ "repo": "<repo-name>", "default_recipients": ["<slack_id>"], "default_channel": null }
```

Patch only the `repos` array — do not rewrite the whole file.
