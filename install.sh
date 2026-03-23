#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
HOOK_CMD="python3 $SCRIPT_DIR/hook.py"
SETTINGS="$HOME/.claude/settings.json"
COMMANDS_DIR="$HOME/.claude/commands"
COMMAND_SRC="$SCRIPT_DIR/feishu-hooks-init.md"
COMMAND_DST="$COMMANDS_DIR/feishu-hooks-init.md"

python3 - "$HOOK_CMD" "$SETTINGS" << 'EOF'
import json, sys, os

hook_cmd = sys.argv[1]
settings_path = sys.argv[2]

# Load or init settings
if os.path.exists(settings_path):
    with open(settings_path) as f:
        settings = json.load(f)
else:
    settings = {}

hooks = settings.setdefault("hooks", {})

# Each entry: (event_name, matcher)
entries = [
    ("Stop",        ".*"),
    ("Notification",".*"),
    ("PreToolUse",  "Bash"),
]

added = []
skipped = []

for event_name, matcher in entries:
    event_hooks = hooks.setdefault(event_name, [])
    # Check if our command is already registered under this event
    already = any(
        h.get("command") == hook_cmd
        for entry in event_hooks
        for h in entry.get("hooks", [])
    )
    if already:
        skipped.append(event_name)
        continue
    # Find existing entry with same matcher, or create new one
    target = next((e for e in event_hooks if e.get("matcher") == matcher), None)
    if target is None:
        target = {"matcher": matcher, "hooks": []}
        event_hooks.append(target)
    target["hooks"].append({"type": "command", "command": hook_cmd})
    added.append(event_name)

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")

if added:
    print(f"✓ Added hooks for: {', '.join(added)}")
if skipped:
    print(f"- Already present: {', '.join(skipped)}")
print(f"  Command: {hook_cmd}")
EOF

# Install the /feishu-hooks-init Claude Code command
mkdir -p "$COMMANDS_DIR"
if [ -f "$COMMAND_DST" ]; then
    echo "- Command already present: $COMMAND_DST"
else
    cp "$COMMAND_SRC" "$COMMAND_DST"
    echo "✓ Installed command: /feishu-hooks-init → $COMMAND_DST"
fi
