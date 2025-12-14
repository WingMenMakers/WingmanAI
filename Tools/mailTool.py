import os
import logging
import json
from google.oauth2.credentials import Credentials 
from googleapiclient.discovery import build
from googleapiclient import errors
from email.mime.text import MIMEText
import base64
from typing import List, Dict, Optional, Tuple, Any
import re # Keep re for email parsing
from datetime import datetime, timedelta

class MailTool:
    # 1. CRITICAL: Accept Credentials object
    def __init__(self, credentials: Credentials): 
        """Initialize with a guaranteed valid Credentials object."""
        self.credentials = credentials
        self.service = self._get_service()
        self._contact_cache = {} 

    # 2. Simplied _get_service
    def _get_service(self):
        """Build the Gmail API service using the provided Credentials."""
        try:
            # The credentials object is guaranteed to be refreshed by the Director/Token Manager
            return build("gmail", "v1", credentials=self.credentials)
        except Exception as e:
            # Raise exception immediately; initialization failure handled by Director
            logging.error(f"Error building Gmail service: {e}")
            raise Exception(f"Gmail service initialization failed: {e}")

    # -------------------- Core Execution Methods --------------------

    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send an email via Gmail API. Returns the raw API response."""
        try:
            message = MIMEText(body, 'plain', 'utf-8')
            message["to"] = to
            message["subject"] = subject

            # Preserve line breaks in the email
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            # Execute send and return the raw response
            sent_message = self.service.users().messages().send(
                userId="me",
                body={'raw': raw_message}
            ).execute()
            
            return sent_message

        except Exception as e:
            # Raise exception on failure
            logging.error(f"Error sending email: {e}")
            raise Exception(f"Failed to send email: {e}")
        
    def reply_to_email(self, message_id: str, to: str, body: str) -> Dict[str, Any]:
        """Reply to an existing email. Returns the raw API response."""
        try:
            # 1. Get original message for threading details
            original = self.service.users().messages().get(
                userId="me", id=message_id, format="metadata", 
                metadataHeaders=["Subject", "References", "Message-ID"]
            ).execute()

            # 2. Extract and format headers
            headers = original["payload"]["headers"]
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"

            # 3. Create reply message
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            message["In-Reply-To"] = message_id
            references = next((h["value"] for h in headers if h["name"] == "References"), "")
            message["References"] = f"{references} {message_id}" if references else message_id

            # 4. Encode and send
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            sent_message = self.service.users().messages().send(
                userId="me",
                body={
                    "raw": raw_message,
                    "threadId": original["threadId"]
                }
            ).execute()

            return sent_message

        except Exception as e:
            # Raise exception on failure
            logging.error(f"Error replying to email: {e}")
            raise Exception(f"Failed to reply to email: {e}")

    # -------------------- Email Retrieval/Parsing Utilities --------------------

    def _get_messages_by_query(self, query: str, max_results: int = 10) -> List[Dict]:
        """Fetch raw email message data using a Gmail query string."""
        try:
            results = self.service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            email_data = []

            for msg in messages:
                # Fetch full message data for extraction
                msg_data = self.service.users().messages().get(
                    userId="me", id=msg["id"], format='full'
                ).execute()
                
                email_data.append(msg_data)
            
            return email_data
            
        except Exception as e:
            logging.error(f"Error fetching messages by query '{query}': {e}")
            # Raise API exception
            raise Exception(f"API query failed: {e}")

    # Fix for get_unread_emails: remove _get_service check
    def get_unread_emails(self, max_results: int = 5) -> List[Dict]:
        """Get unread emails in a structured format."""
        raw_messages = self._get_messages_by_query("is:unread", max_results)
        
        # Structure and return the raw data
        return [self._extract_email_parts(msg) for msg in raw_messages]
        
    def get_emails_from_sender(self, sender_query: str, max_results: int = 10) -> List[Dict]:
        """Fetch emails from a specific sender (by name or email)."""
        # Determine query: Gmail handles 'from:name' or 'from:email' well.
        query = f"from:{sender_query}"
        
        raw_messages = self._get_messages_by_query(query, max_results)
        
        # Structure and return the raw data
        return [self._extract_email_parts(msg) for msg in raw_messages]
    
    def search_emails(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search emails using Gmail's search syntax."""
        raw_messages = self._get_messages_by_query(query, max_results)
        
        # Structure and return the raw data
        return [self._extract_email_parts(msg) for msg in raw_messages]
    
    def get_thread(self, thread_id: str) -> List[Dict]:
        """Get all messages in a thread."""
        try:
            thread = self.service.users().threads().get(
                userId='me', id=thread_id, format='full'
            ).execute()

            # Structure and return the raw data
            return [self._extract_email_parts(message) for message in thread['messages']]

        except Exception as e:
            logging.error(f"Error fetching thread: {e}")
            raise Exception(f"Failed to fetch thread: {e}")
        
    def mark_as_read(self, email_ids: str | List[str]) -> bool:
        """Mark emails as read. Returns True on success, False on API error."""
        if isinstance(email_ids, str):
            email_ids = [email_ids]
            
        try:
            # We use a single batch modify call for robustness
            self.service.users().messages().batchModify(
                userId="me",
                body={
                    "ids": email_ids,
                    "removeLabelIds": ["UNREAD"]
                }
            ).execute()
            return True
        except Exception as e:
            logging.error(f"Error marking emails as read: {e}")
            return False # Return boolean on this specific API action
        
    # -------------------- Contact Resolution/Profile --------------------

    def get_contact_suggestions_raw(self, name_query: str) -> List[Tuple[str, str]]:
        """
        Get email suggestions based on name query. Returns a raw list of (Name, Email) tuples.
        """
        name_key = name_query.lower()
        if name_key in self._contact_cache:
            return self._contact_cache[name_key]

        try:
            # Search in sent and received emails
            query = f"from:{name_query} OR to:{name_query}"
            results = self.service.users().messages().list(
                userId="me", q=query, maxResults=10
            ).execute()

            messages = results.get("messages", [])
            email_addresses = set()

            for msg in messages:
                email_data = self.service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata", 
                    metadataHeaders=["From", "To"]
                ).execute()

                headers = email_data["payload"]["headers"]
                
                for header in headers:
                    if header["name"] in ["From", "To"]:
                        # _extract_email_addresses returns [(name, email)]
                        addresses = self._extract_email_addresses(header["value"]) 
                        for name, email in addresses:
                             if name_key in name.lower() or name_key in email.lower().split('@')[0]:
                                 email_addresses.add((name, email))

            valid_emails = [
                (name, email) for name, email in email_addresses 
                if not any(x in email.lower() for x in [
                    'noreply', 'linkedin', 'drive-shares', 'invitations', 'maps.google'
                ])
            ]
            
            self._contact_cache[name_key] = valid_emails
            return valid_emails

        except Exception as e:
            logging.error(f"Error getting email suggestions: {e}")
            raise Exception(f"Contact suggestion API failed: {e}")
        
    def get_sender_profile(self) -> Dict[str, Optional[str]]:
        """Get sender's profile information. Returns Dict of raw data."""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            
            # Note: Gmail API often doesn't give the full name directly.
            display_name = profile.get('emailAddress', '').split('@')[0].replace('.', ' ').title()
            
            return {
                'email': profile.get('emailAddress'),
                'name': display_name
            }
        
        except Exception as e:
            logging.error(f"Error getting sender profile: {e}")
            raise Exception(f"Profile API failed: {e}")
    
    # -------------------- Internal Helpers (Moved/Simplified) --------------------

    def _get_email_body(self, message: Dict) -> str:
        """Extract email body in a cleaner format."""
        # Using a safer, more comprehensive approach for body extraction
        if 'data' in message['body']:
            return base64.urlsafe_b64decode(message['body']['data']).decode('utf-8').strip()

        if 'parts' in message:
            for part in message['parts']:
                mime_type = part.get('mimeType', '').lower()
                if mime_type == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8').strip()
                elif mime_type.startswith('multipart'):
                    # Recursively check multi-part messages
                    result = self._get_email_body(part)
                    if result: return result
        
        return "No readable content"
    
    def _extract_email_parts(self, msg_data: Dict) -> Dict:
        """Extract relevant structured parts from the raw Gmail API message data."""
        
        # Fallback for when the payload might be the message itself
        payload = msg_data.get('payload', msg_data)

        headers = payload.get("headers", [])
        
        # Use a dict comprehension for efficient header lookup
        header_map = {h["name"].lower(): h["value"] for h in headers}

        # Extract body using the helper function
        body = self._get_email_body(payload)

        return {
            "id": msg_data.get("id", "N/A"),
            "thread_id": msg_data.get("threadId", "N/A"),
            "subject": header_map.get("subject", "No Subject"),
            "sender": header_map.get("from", "Unknown Sender"),
            "date": header_map.get("date", ""),
            "body": body
        }

    def _extract_email_addresses(self, header_value: str) -> list:
        """Extract name and email from header value."""
        results = []
        # Handle multiple addresses separated by commas
        for addr in header_value.split(","):
            addr = addr.strip()
            # Match patterns like: "Name <email@domain.com>" or "email@domain.com"
            match = re.search(r'^(.*?)<(.+?)>$', addr)
            if match:
                name = match.group(1).strip().strip('"')
                email = match.group(2).strip()
                results.append((name, email))
            elif "@" in addr:
                 # If it's just an email, use the email as the name
                results.append((addr, addr))
        return results
