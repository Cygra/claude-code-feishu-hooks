#!/usr/bin/env python3
"""
feishu-hooks/hook.py — Claude Code hook handler
Reads hook event JSON from stdin, sends Feishu card notification.

Registered for: Stop, Notification, StopFailure, PreToolUse (Bash)
Config: ~/.claude/feishu.json
"""

import json
import os
import sys
import urllib.request
from datetime import datetime

CONFIG_PATH = os.path.expanduser("~/.claude/feishu.json")
BASE_URL = "https://open.feishu.cn/open-apis"

EVENT_COLORS = {
    "task_complete": "green",
    "needs_confirm": "orange",
    "error":         "red",
    "info":          "grey",
}

EVENT_ICONS = {
    "task_complete": "✅",
    "needs_confirm": "⚠️",
    "error":         "❌",
    "info":          "ℹ️",
}

DANGEROUS_PATTERNS = [
    "rm -rf",
    "git push -f",
    "git push --force",
    "git reset --hard",
    "drop table",
    "delete from",
    "truncate table",
]


def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"feishu-hooks: config not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def http_request(url, payload, method, headers=None):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"feishu-hooks: request failed: {e}", file=sys.stderr)
        sys.exit(1)


def get_token(app_id, app_secret):
    url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
    resp = http_request(url, {"app_id": app_id, "app_secret": app_secret}, "POST")
    if resp.get("code") != 0:
        print(f"feishu-hooks: failed to get token: {resp}", file=sys.stderr)
        sys.exit(1)
    return resp["tenant_access_token"]


def build_card(event, title, body, cwd=""):
    color = EVENT_COLORS.get(event, "grey")
    icon = EVENT_ICONS.get(event, "")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    home = os.path.expanduser("~")
    cwd_part = f"  ·  {cwd.replace(home, '~')}" if cwd else ""
    content = f"{body}\n\n---\n<font color='grey'>Claude Code  ·  {timestamp}{cwd_part}</font>"

    return {
        "schema": "2.0",
        "config": {
            "update_multi": True,
        },
        "header": {
            "title": {"tag": "plain_text", "content": f"{icon} {title}"},
            "subtitle": {"tag": "plain_text", "content": ""},
            "template": color,
            "padding": "12px 12px 12px 12px",
        },
        "body": {
            "direction": "vertical",
            "padding": "12px 12px 12px 12px",
            "elements": [
                {
                    "tag": "markdown",
                    "content": content,
                    "text_align": "left",
                    "text_size": "normal_v2",
                    "margin": "0px 0px 0px 0px",
                },
            ],
        },
    }


def send_feishu(event, title, body, cwd=""):
    config = load_config()
    token = get_token(config["app_id"], config["app_secret"])
    card = build_card(event, title, body, cwd)
    card = enforce_card_limit(card)
    card_json = json.dumps(card, ensure_ascii=False)
    user_id_type = config.get("user_id_type", "user_id")
    url = f"{BASE_URL}/im/v1/messages?receive_id_type={user_id_type}"
    payload = {
        "receive_id": config["user_id"],
        "msg_type": "interactive",
        "content": card_json,
    }
    resp = http_request(url, payload, "POST", {"Authorization": f"Bearer {token}"})
    if resp.get("code") != 0:
        print(f"feishu-hooks: failed to send message: {resp}", file=sys.stderr)
        sys.exit(1)


CARD_LIMIT_BYTES = 30 * 1024  # feishu card limit: 30 KB
TRUNCATE_SUFFIX = "…\n\n<font color='grey'>（内容超过 30KB 已截断）</font>"
_SUFFIX_BYTES = len(TRUNCATE_SUFFIX.encode("utf-8"))


PLAN_APPROVAL_MESSAGE = "Claude Code needs your approval for the plan"


def get_plan_content(transcript_path: str) -> str:
    """Extract planFilePath from ExitPlanMode tool_use block in transcript and return the plan file content."""
    try:
        plan_file = None
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for block in entry.get("message", {}).get("content", []):
                    if isinstance(block, dict) and block.get("name") == "ExitPlanMode":
                        path = block.get("input", {}).get("planFilePath")
                        if path:
                            plan_file = path
        if not plan_file or not os.path.exists(plan_file):
            return ""
        with open(plan_file) as f:
            return f.read()
    except Exception:
        return ""


def enforce_card_limit(card: dict) -> dict:
    """Ensure the serialized card JSON is within 30 KB. Trims markdown content if needed."""
    card_json = json.dumps(card, ensure_ascii=False)
    encoded = card_json.encode("utf-8")
    if len(encoded) <= CARD_LIMIT_BYTES:
        return card
    # Overage measured in JSON bytes; trimming raw UTF-8 bytes is conservative
    # (raw bytes <= JSON bytes due to escaping), so result stays within limit.
    element = card["body"]["elements"][0]
    content = element["content"]
    overage = len(encoded) - CARD_LIMIT_BYTES + _SUFFIX_BYTES
    content_bytes = content.encode("utf-8")
    trimmed = content_bytes[: max(0, len(content_bytes) - overage)].decode("utf-8", errors="ignore")
    element["content"] = trimmed + TRUNCATE_SUFFIX
    return card


def main():
    try:
        event = json.load(sys.stdin)
    except Exception as e:
        print(f"feishu-hooks: failed to parse stdin JSON: {e}", file=sys.stderr)
        sys.exit(1)

    hook_name = event.get("hook_event_name", "")
    cwd = event.get("cwd", "")

    if hook_name == "Stop":
        if event.get("stop_hook_active"):
            sys.exit(0)
        last_msg = event.get("last_assistant_message", "（无消息）")
        send_feishu("task_complete", "任务完成", last_msg, cwd)

    elif hook_name == "Notification":
        notif_type = event.get("notification_type", "")
        message = event.get("message", "")
        title = event.get("title", "通知")

        if message == PLAN_APPROVAL_MESSAGE:
            plan = get_plan_content(event.get("transcript_path", ""))
            body = plan if plan else "（无法读取 plan 内容）"
            send_feishu("needs_confirm", "📋 Plan 待审批", body, cwd)
        elif notif_type == "permission_prompt":
            send_feishu("needs_confirm", title or "需要权限确认", message)
        elif notif_type == "idle_prompt":
            send_feishu("info", "等待输入", message)
        # auth_success and elicitation_dialog are not actionable — skip

    elif hook_name == "PreToolUse" and event.get("tool_name") == "Bash":
        cmd = event.get("tool_input", {}).get("command", "")
        cmd_lower = cmd.lower()
        matched = next((p for p in DANGEROUS_PATTERNS if p in cmd_lower), None)
        if matched:
            desc = event.get("tool_input", {}).get("description", "")
            body = f"检测到危险操作，即将执行：\n\n```\n{cmd}\n```"
            if desc:
                body += f"\n\n描述：{desc}"
            send_feishu("needs_confirm", "危险操作提醒", body)


if __name__ == "__main__":
    main()
