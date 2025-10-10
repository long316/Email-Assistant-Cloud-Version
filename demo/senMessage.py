import base64
import os.path
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def gmail_send_message():
  """Create and send an email message
  Print the returned  message id
  Returns: Message object, including message id

  Load pre-authorized user credentials from the environment.
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
    # create gmail api client
    service = build("gmail", "v1", credentials=creds)

    message = EmailMessage()

    # --- 邮件内容，请修改为您自己的 ---
    message.set_content("This is an automated email sent by Python script.")
    message["To"] = "johnloneyy@gmail.com"  # 收件人
    message["From"] = "junoliii98@gmail.com" # 您的发件邮箱
    message["Subject"] = "Test Email from Gmail API"
    # --- 邮件内容结束 ---

    # encoded message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    create_message = {"raw": encoded_message}
    
    # pylint: disable=E1101
    send_message = (
        service.users()
        .messages()
        .send(userId="me", body=create_message)
        .execute()
    )
    print(f'Message Id: {send_message["id"]}')
  
  except HttpError as error:
    print(f"An error occurred: {error}")
    send_message = None
  
  return send_message

if __name__ == "__main__":
  gmail_send_message()