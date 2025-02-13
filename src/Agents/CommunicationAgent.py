import openai
import json
from Tools.MailTool import MailTool
from dotenv import load_dotenv
import os

load_dotenv()

class CommunicationManager:
    def __init__(self, mail_tool):
        """Initialize with MailTool for email actions."""
        self.mail_tool = mail_tool
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Updated OpenAI API client

    def generate_email(self, prompt):
        """Generate an email body using OpenAI's API."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that drafts professional and concise emails."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating email: {e}"

    def send_email(self, recipient, subject, user_query):
        """Generate and send an email based on user query."""
        email_body = self.generate_email(user_query)

        if "Error" in email_body:
            return email_body  # Return error if email generation failed

        return self.mail_tool.send_email(recipient, subject, email_body)

    def read_unread_emails(self):
        """Read unread emails."""
        return self.mail_tool.read_emails()

    def handle_request(self, user_query):
        """Process the user's request using LLM and call the appropriate function."""
        try:
            # **Step 1: Ask OpenAI to determine the intent (returns a string)**
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an AI that determines the user's intent. "
                                                  "Respond with ONLY valid JSON in this format: "
                                                  '{"task": "send_email"} or {"task": "read_emails"}'},
                    {"role": "user", "content": f"Determine the task for this request: '{user_query}'"}
                ]
            )

            # **Step 2: Get response text and parse JSON**
            response_text = response.choices[0].message.content.strip()

            try:
                intent_data = json.loads(response_text)  # Convert JSON string to Python dict
                task = intent_data.get("task", "unknown")
            except json.JSONDecodeError:
                print("OpenAI response is not valid JSON:", response_text)  # Debugging log
                task = "unknown"

            # **Step 3: Take action based on intent**
            if task == "send_email":
                return self.send_email("AnujSharad.Mankumare_2026@woxsen.edu.in", "Update on WingMan Project", user_query)
            elif task == "read_emails":
                return self.read_unread_emails()
            else:
                return "I'm not sure what action to take. Can you rephrase your request?"

        except Exception as e:
            return f"Error handling request: {e}"
