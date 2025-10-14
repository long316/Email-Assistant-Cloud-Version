 # OAuth 部署指南（服务器 Web 授权流程）

 本指南介绍如何在服务器环境下完成 Gmail OAuth Web 授权，使用户在浏览器中完成授权，服务端接收回调并保存刷新令牌。

 ## 一、在 Google Cloud Console 配置
 1. 创建 OAuth 同意屏幕（内部/外部，根据使用场景选择）。
 2. 创建 OAuth 客户端：类型选择「Web application」。
 3. 在「授权的重定向 URI」添加：`https://your-domain.com/oauth/google/callback`（与你部署环境一致）。
 4. 下载客户端凭据 JSON，配置到环境变量 `GOOGLE_OAUTH_CLIENT_JSON`。

 最小权限 Scope：`https://www.googleapis.com/auth/gmail.send`

## 二、服务端环境变量
- `AUTH_FLOW=web`
- `GOOGLE_OAUTH_CLIENT_JSON=/path/to/client_secret.json`
- `OAUTH_REDIRECT_URL=https://your-domain.com/oauth/google/callback`
- （可选）`ENCRYPTION_KEY=...`（令牌加密密钥）
 - `API_KEY=...`（启用后，需在请求头携带 `X-API-Key`）

 ## 三、授权流程（用户视角）
 1. 在达人管理系统点击「连接 Gmail」。
 2. 浏览器跳转到：`GET /oauth/google/authorize?sender_email=xxx@gmail.com`。
 3. 系统重定向用户到 Google 授权页，用户登录并点击「同意」。
 4. Google 回调：`GET /oauth/google/callback?code=...&state=...`
 5. 服务端用 `code` 交换令牌，验证邮箱地址，保存 refresh token。
 6. 后续发送使用 refresh token 静默刷新，无需再次跳转。

 提示：首次授权需 `prompt=consent` 才能获得 refresh token；同一账号频繁创建令牌会导致旧令牌失效，建议每账号仅维护一份 refresh token。

## 四、接口说明
- `GET /oauth/google/authorize?sender_email=...`
   - 生成授权 URL 并 302 重定向至 Google 授权页。
- `GET /oauth/google/callback?code=...&state=...`
   - 用授权码换取令牌，保存后返回绑定结果（JSON）。

 调用发送接口示例（开启 API Key 时）
 ```bash
 curl -X POST https://your-domain.com/api/send_emails \
   -H 'Content-Type: application/json' \
   -H 'X-API-Key: <your_api_key>' \
   -d '{
     "sender_email": "your@gmail.com",
     "excel_file_path": "data.xlsx",
     "subject": "Hello",
     "content": "Hi",
     "attachments": ["product_catalog.pdf"]
   }'
 ```

 ## 五、注意事项
 - HTTPS：回调 URL 必须为 HTTPS（生产环境）。
 - 同意屏幕验证：若对外提供，受限/敏感 scope 需要通过 Google 验证；内部（Workspace）可设为 Internal。
 - 最小化权限：仅申请 `gmail.send`，后续需要再逐步添加。
 - 安全：建议对 `state` 做签名校验以防 CSRF（后续版本增强）。
