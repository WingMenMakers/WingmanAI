import os
import time  
import requests
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv 

# Load environment variables
load_dotenv()

class MailTool:
    def __init__(self):
        """Initialize with OAuth credentials and authenticate Gmail API."""
        self.client_id = os.getenv("GMAIL_CLIENT_ID")
        self.client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        self.refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
        self.access_token = None
        self.token_expiry = 0  
        self.service = None  # Store the Gmail API service instance

        self.authenticate()  # Auto-authenticate on init

    def get_access_token(self):
        """Refresh and return a valid access token, caching it until it expires."""
        current_time = time.time()

        # If token is still valid, return it
        if self.access_token and current_time < self.token_expiry:
            return self.access_token

        # Otherwise, refresh the token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }

        response = requests.post(token_url, data=data)
        token_data = response.json()

        if "access_token" not in token_data:
            raise Exception("Error fetching access token! Check credentials.")

        # Store new access token and expiry time
        self.access_token = token_data["access_token"]
        self.token_expiry = current_time + token_data.get("expires_in", 3600) - 60  # Subtract 60s buffer

        return self.access_token

    def authenticate(self):
        """Authenticate Gmail API using the access token and store service instance."""
        access_token = self.get_access_token()  # Get fresh token
        creds = Credentials(access_token)  # Use Credentials from google.oauth2
        self.service = build("gmail", "v1", credentials=creds)  # Store service

    def send_email(self, to, subject, body):
        """Send an email via Gmail API."""
        try:
            if not self.service:
                self.authenticate()  # Ensure service is initialized

            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            response = self.service.users().messages().send(
                userId="me", body={"raw": raw_message}
            ).execute()

            return f"Email sent! Message ID: {response['id']}"
        except Exception as e:
            return f"Error sending email: {e}"

    def read_emails(self, query="is:unread", max_results=5):
        """Fetch unread emails from Gmail."""
        try:
            if not self.service:
                self.authenticate()  # Ensure service is initialized

            results = self.service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            email_data = []

            for msg in messages:
                msg_data = self.service.users().messages().get(
                    userId="me", id=msg["id"]
                ).execute()
                headers = msg_data["payload"]["headers"]

                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")

                email_data.append({"from": sender, "subject": subject, "id": msg["id"]})

            return email_data if email_data else "No new emails found."
        except Exception as e:
            return f"Error reading emails: {e}"
