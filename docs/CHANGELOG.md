 # 变更记录

## Unreleased
- 新增：服务器环境 OAuth Web 授权流程与路由文档（docs/OAuth部署指南.md）。
- 新增：`/oauth/google/authorize` 与 `/oauth/google/callback` 路由（服务端发件人绑定）。
- 修复：传统发送模式贯通 `attachments` 参数至实际发送逻辑。
- 扩展：`/api/send_template_emails` 端点支持 `attachments` 参数。
- 说明：命令行已支持附件参数，通过 `--attachments` 传入多个文件（空格分隔）。
- 新增：OpenAPI 3.0 规范文件（docs/openapi.yaml），覆盖当前所有端点与 API Key 鉴权。
