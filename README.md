# claude-code-feishu-hooks

Claude Code 飞书通知 hooks。基于 Claude Code 的 [hooks 机制](https://docs.anthropic.com/en/docs/claude-code/hooks)，在任务完成、需要确认等关键节点自动向飞书发送通知卡片。

相比 skill 方式，hooks 由 Claude Code 系统直接触发，无需 AI 判断，**稳定可靠**。

## 通知类型

| 触发时机 | 卡片颜色 | 说明 |
|---|---|---|
| Claude 完成回答（`Stop`） | 🟢 绿色 | 任务完成，附带最后一条消息摘要 |
| 需要权限确认（`Notification` permission_prompt） | 🟠 橙色 | Claude 等待用户在终端确认操作 |
| Claude 等待输入（`Notification` idle_prompt） | ⚪ 灰色 | Claude 已就绪，等待下一条指令 |
| 执行危险命令前（`PreToolUse` Bash） | 🟠 橙色 | 检测到 `rm -rf`、force push 等危险操作 |

检测的危险命令模式：`rm -rf`、`git push -f`、`git push --force`、`git reset --hard`、`DROP TABLE`、`DELETE FROM`、`truncate table`

## 前置条件

需要 `~/.claude/feishu.json` 配置文件。

安装后可直接在 Claude Code 中运行 `/feishu-hooks-init` 命令，由 Claude 引导填写，无需手动编辑文件。

也可以手动创建：

```json
{
  "app_id": "cli_xxx",
  "app_secret": "your_secret",
  "user_id": "your_user_id",
  "user_id_type": "user_id"
}
```

**获取步骤：**

1. 前往[飞书开放平台](https://open.feishu.cn/app)，创建一个自建应用
2. 在「凭证与基础信息」里获取 `app_id` 和 `app_secret`
3. 在「权限管理」里开通 `im:message:send_as_bot`（发送消息）权限，并发版
4. 你的 `user_id` 可在飞书 App → 个人资料 → 复制用户 ID 获取

字段说明：
- `app_id` / `app_secret`：飞书自建应用的 App ID 和 Secret
- `user_id`：接收通知的用户 ID
- `user_id_type`：ID 类型，通常为 `user_id`（也支持 `open_id`、`union_id`）

## 安装

```bash
bash install.sh
```

install.sh 会自动检测脚本所在路径，将 `hook.py` 的**绝对路径**写入 `~/.claude/settings.json`。

安装后的 settings.json 示例：

```json
{
  "hooks": {
    "Stop": [
      { "matcher": ".*", "hooks": [{ "type": "command", "command": "python3 /path/to/claude-code-feishu-hooks/hook.py" }] }
    ],
    "Notification": [
      { "matcher": ".*", "hooks": [{ "type": "command", "command": "python3 /path/to/claude-code-feishu-hooks/hook.py" }] }
    ],
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "python3 /path/to/claude-code-feishu-hooks/hook.py" }] }
    ]
  }
}
```

安装是**幂等**的，重复执行不会产生重复条目。不会影响其他已有的 hooks。

install.sh 同时会将 `/feishu-hooks-init` 命令安装到 `~/.claude/commands/`，安装后在任意 Claude Code 会话中输入该命令，Claude 会引导你填写飞书应用凭证并写入配置文件，无需手动编辑 JSON。

## 卸载

```bash
bash uninstall.sh
```

仅移除 claude-code-feishu-hooks 注册的条目，其他 hooks 保持不变。

## 手动配置

如果不想用安装脚本，可以直接编辑 `~/.claude/settings.json`，在 `hooks` 对象里加入上面的 JSON 片段，将路径替换为实际的 `hook.py` 绝对路径。

## 禁用某个事件

直接在 `~/.claude/settings.json` 中删除对应的 hook 条目即可。例如，不想在任务完成时通知，删掉 `Stop` 下对应的 hook 对象。
