帮用户配置飞书通知所需的 `~/.claude/feishu.json` 文件。

步骤：

1. 检查 `~/.claude/feishu.json` 是否已存在，如果存在则读取并展示当前值（app_secret 显示为 `***` 脱敏）。

2. 用 AskUserQuestion 向用户收集以下信息（如有已有值，提示当前值，用户可直接跳过保留原值）：
   - **App ID**：飞书自建应用的 app_id（格式通常为 `cli_xxx`）
   - **App Secret**：飞书自建应用的 app_secret
   - **User ID**：接收通知的飞书用户 ID
   - **User ID Type**：ID 类型，选项为 `user_id`（默认）、`open_id`、`union_id`

3. 将信息写入 `~/.claude/feishu.json`：
   ```json
   {
     "app_id": "...",
     "app_secret": "...",
     "user_id": "...",
     "user_id_type": "..."
   }
   ```

4. 完成后提示用户：配置已保存，如果还没运行 `install.sh`，可以运行 `bash <feishu-hooks 目录>/install.sh` 注册 hooks。

注意：写文件时确保 `~/.claude/` 目录存在。
