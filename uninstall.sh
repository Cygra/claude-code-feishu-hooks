#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
HOOK_CMD="python3 $SCRIPT_DIR/hook.py"
SETTINGS="$HOME/.claude/settings.json"
COMMAND_DST="$HOME/.claude/commands/feishu-hooks-init.md"

if [ ! -f "$SETTINGS" ]; then
    echo "Nothing to do: $SETTINGS does not exist."
    exit 0
fi

python3 - "$HOOK_CMD" "$SETTINGS" << 'EOF'
import json, sys

hook_cmd = sys.argv[1]
settings_path = sys.argv[2]

with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.get("hooks", {})
removed = []

for event_name, event_hooks in hooks.items():
    for entry in event_hooks:
        before = len(entry.get("hooks", []))
        entry["hooks"] = [h for h in entry.get("hooks", []) if h.get("command") != hook_cmd]
        after = len(entry["hooks"])
        if after < before:
            removed.append(event_name)

# Clean up empty hook entries
for event_name in list(hooks.keys()):
    hooks[event_name] = [e for e in hooks[event_name] if e.get("hooks")]
    if not hooks[event_name]:
        del hooks[event_name]

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")

if removed:
    print(f"✓ Removed hooks for: {', '.join(dict.fromkeys(removed))}")
else:
    print("- No feishu-hooks entries found.")
EOF

# Remove the /feishu-hooks-init command
if [ -f "$COMMAND_DST" ]; then
    rm "$COMMAND_DST"
    echo "✓ Removed command: $COMMAND_DST"
else
    echo "- Command not found: $COMMAND_DST"
fi
