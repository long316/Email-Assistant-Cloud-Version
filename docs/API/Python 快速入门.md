# Python 快速入门

创建一个向 Gmail API 发出请求的 Python 命令行应用。

快速入门介绍了如何设置和运行调用 Google Workspace API 的应用。本快速入门使用一种简化的身份验证方法，该方法适用于测试环境。对于生产环境，我们建议您先了解[身份验证和授权](https://developers.google.com/workspace/guides/auth-overview?hl=zh-cn)，然后再[选择适合您应用的访问凭据](https://developers.google.com/workspace/guides/create-credentials?hl=zh-cn#choose_the_access_credential_that_is_right_for_you)。

本快速入门使用 Google Workspace 推荐的 API 客户端库来处理身份验证和授权流程的一些细节。

## 目标

- 设置环境。
- 安装客户端库。
- 设置示例。
- 运行示例。

## 前提条件

如需运行本快速入门，您需要满足以下前提条件：

- Python 3.10.7 或更高版本
- [pip](https://pypi.python.org/pypi/pip) 软件包管理工具
- [Google Cloud 项目](https://developers.google.com/workspace/guides/create-project?hl=zh-cn)。



- 已启用 Gmail 的 Google 账号。



## 设置环境

如需完成本快速入门，请设置您的环境。

### 启用 API

在使用 Google API 之前，您需要在 Google Cloud 项目中将其开启。 您可以在单个 Google Cloud 项目中启用一个或多个 API。

- 在 Google Cloud 控制台中，启用 Gmail API。

  [启用 API](https://console.cloud.google.com/flows/enableapi?apiid=gmail.googleapis.com&hl=zh-cn)

### 配置 OAuth 权限请求页面

如果您要使用新的 Google Cloud 项目完成本快速入门，请配置 OAuth 同意屏幕。如果您已为 Cloud 项目完成此步骤，请跳至下一部分。

1. 在 Google Cloud 控制台中，依次前往菜单 menu > **Google Auth platform** > **品牌推广**。

   [前往“品牌推广”](https://console.cloud.google.com/auth/branding?hl=zh-cn)

2. 如果您已配置 Google Auth platform，则可以在[品牌](https://console.cloud.google.com/auth/branding?hl=zh-cn)、[受众群体](https://console.cloud.google.com/auth/audience?hl=zh-cn)和[数据访问](https://console.cloud.google.com/auth/scopes?hl=zh-cn)中配置以下 OAuth 权限请求页面设置。如果您看到一条消息，指出**Google Auth platform 尚未配置**，请点击**开始**：

   1. 在**应用信息**下，在**应用名称**中输入应用的名称。
   2. 在**用户支持电子邮件**中，选择一个支持电子邮件地址，以便用户在对自己的同意情况有疑问时与您联系。
   3. 点击**下一步**。
   4. 在**受众群体**下，选择**内部**。
   5. 点击**下一步**。
   6. 在**联系信息**下，输入一个**电子邮件地址**，以便您接收有关项目变更的通知。
   7. 点击**下一步**。
   8. 在**完成**部分，查看 [Google API 服务用户数据政策](https://developers.google.com/terms/api-services-user-data-policy?hl=zh-cn)，如果您同意该政策，请选择**我同意《Google API 服务：用户数据政策》**。
   9. 点击**继续**。
   10. 点击**创建**。

3. 目前，您可以跳过添加范围的步骤。 未来，如果您创建的应用供 Google Workspace 组织以外的用户使用，则必须将**用户类型**更改为**外部**。然后，添加应用所需的授权范围。如需了解详情，请参阅完整的[配置 OAuth 同意](https://developers.google.com/workspace/guides/configure-oauth-consent?hl=zh-cn)指南。

### 为桌面应用授权凭据

如需对最终用户进行身份验证并访问应用中的用户数据，您需要创建一个或多个 OAuth 2.0 客户端 ID。客户端 ID 用于向 Google 的 OAuth 服务器标识单个应用。如果您的应用在多个平台上运行，您必须为每个平台分别创建客户端 ID。

1. 在 Google Cloud 控制台中，依次前往“菜单”图标 menu > **Google Auth platform** > **客户端**。

   [前往“客户”页面](https://console.cloud.google.com/auth/clients?hl=zh-cn)

2. 点击**创建客户端**。

3. 依次点击**应用类型** > **桌面应用**。

4. 在**名称**字段中，输入凭据的名称。此名称仅在 Google Cloud 控制台中显示。

5. 点击**创建**。

   新创建的凭据会显示在“OAuth 2.0 客户端 ID”下。

6. 将下载的 JSON 文件另存为 `credentials.json`，然后将该文件移动到您的工作目录。

## 安装 Google 客户端库

- 安装 Python 版 Google 客户端库：

  

  ```
  pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
  ```

## 配置示例

1. 在工作目录中，创建一个名为 `quickstart.py` 的文件。

2. 在 `quickstart.py` 中添加以下代码：

   gmail/quickstart/quickstart.py

   [在 GitHub 上查看](https://github.com/googleworkspace/python-samples/blob/main/gmail/quickstart/quickstart.py)

   ```
   import os.path
   
   from google.auth.transport.requests import Request
   from google.oauth2.credentials import Credentials
   from google_auth_oauthlib.flow import InstalledAppFlow
   from googleapiclient.discovery import build
   from googleapiclient.errors import HttpError
   
   # If modifying these scopes, delete the file token.json.
   SCOPES = ["https://mail.google.com/"]
   
   
   def main():
     """Shows basic usage of the Gmail API.
     Lists the user's Gmail labels.
     """
     creds = None
     # The file token.json stores the user's access and refresh tokens, and is
     # created automatically when the authorization flow completes for the first
     # time.
     if os.path.exists("token.json"):
       creds = Credentials.from_authorized_user_file("token.json", SCOPES)
     # If there are no (valid) credentials available, let the user log in.
     if not creds or not creds.valid:
       if creds and creds.expired and creds.refresh_token:
         creds.refresh(Request())
       else:
         flow = InstalledAppFlow.from_client_secrets_file(
             "credentials.json", SCOPES
         )
         creds = flow.run_local_server(port=0)
       # Save the credentials for the next run
       with open("token.json", "w") as token:
         token.write(creds.to_json())
   
     try:
       # Call the Gmail API
       service = build("gmail", "v1", credentials=creds)
       results = service.users().labels().list(userId="me").execute()
       labels = results.get("labels", [])
   
       if not labels:
         print("No labels found.")
         return
       print("Labels:")
       for label in labels:
         print(label["name"])
   
     except HttpError as error:
       # TODO(developer) - Handle errors from gmail API.
       print(f"An error occurred: {error}")
   
   
   if __name__ == "__main__":
     main()
   ```

   

   

## 运行示例

1. 在工作目录中，构建并运行示例：

   ```
   python3 quickstart.py
   ```

1. 首次运行该示例时，系统会提示您授权访问：

   1. 如果您尚未登录 Google 账号，请在系统提示时登录。如果您登录了多个账号，请选择一个账号用于授权。
   2. 点击**接受**。

   您的 Python 应用运行并调用 Gmail API。

   授权信息存储在文件系统中，因此下次运行示例代码时，系统不会提示您进行授权。