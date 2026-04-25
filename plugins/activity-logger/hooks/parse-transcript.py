#!/usr/bin/env python3
"""Parse a Claude Code session transcript JSONL into condensed text for summarization."""

import json
import sys
from collections import Counter

MAX_CHARS = 50000

def parse_transcript(jsonl_path):
    user_messages = []
    assistant_texts = []
    tool_counts = Counter()
    line_count = 0

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            line_count += 1
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type", "")
            message = entry.get("message", {})
            content = message.get("content", "")

            if entry_type == "user" and isinstance(content, str) and content.strip():
                user_messages.append(content.strip())

            elif entry_type == "assistant" and isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text", "").strip():
                        assistant_texts.append(block["text"].strip())
                    elif block.get("type") == "tool_use":
                        tool_counts[block.get("name", "unknown")] += 1

    if line_count == 0:
        return ""

    parts = []

    parts.append("=== USER PROMPTS ===")
    for msg in user_messages:
        parts.append(f"User: {msg[:500]}")

    parts.append("\n=== ASSISTANT RESPONSES ===")
    for text in assistant_texts:
        parts.append(f"Assistant: {text[:500]}")

    if tool_counts:
        parts.append("\n=== TOOLS USED ===")
        for tool, count in tool_counts.most_common():
            parts.append(f"  {tool}: {count}x")

    output = "\n".join(parts)
    if len(output) > MAX_CHARS:
        output = output[:MAX_CHARS] + "\n... (truncated)"

    return output


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <transcript.jsonl>", file=sys.stderr)
        sys.exit(1)

    result = parse_transcript(sys.argv[1])
    print(result)
