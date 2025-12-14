import os
import json
import logging
from openai import OpenAI
from Tools.mailTool import MailTool # Corrected import path for clarity
from typing import List, Dict, Optional, Any
from google.oauth2.credentials import Credentials # NEW: Import Credentials for type hinting
from dotenv import load_dotenv

load_dotenv()

class EmailAgent:
    def __init__(self, credentials: Credentials): 
        # CRITICAL FIX: Pass the credentials to the MailTool
        self.mail_tool = MailTool(credentials=credentials) 
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sender_name = self._get_sender_name()
    
    # --------------------------------------------------------------------------
    # NOTE: The method name 'EmailAgent' below must be renamed to adhere to Python standards
    # and to avoid confusion with the class name. We will rename it to '_analyze_query_to_json'.
    # --------------------------------------------------------------------------

    # -------------------- LLM Task Parsing (Internal Tool) --------------------

    def _analyze_query_to_json(self, user_query):
        """Uses LLM to parse the user query into a structured action/params JSON."""
        system_prompt = (
    "You are an intelligent Email Agent that helps users manage their emails effectively.\n\n"

    "Your job is to **understand the user's request** and output a **valid JSON object** with exactly two keys:\n"
    "{\n"
    '  "action": "action_type",\n'
    '  "params": { key-value pairs based on the action }\n'
    "}\n\n"

    "Supported actions (as string values under the 'action' key):\n"
    "- \"send\": Compose and send a new email\n"
    "- \"reply\": Reply to a specific email\n"
    "- \"forward\": Forward an email to someone else\n"
    "- \"read\": Show unread or specific emails\n"
    "- \"delete\": Delete an email by ID or subject\n"
    "- \"search\": Search emails based on sender, subject, or keyword\n\n"

    "The `params` dictionary can include the following keys, depending on the action:\n"
    "- \"to\": recipient email address(es) (for send, forward)\n"
    "- \"subject\": subject line (for send, search, delete)\n"
    "- \"body\": content of the message (for send, reply, forward)\n"
    "- \"message_id\": unique ID of the email (for reply, forward, delete)\n"
    "- \"sender\": sender's name or email (for search, read)\n"
    "- \"query\": short summary of what the message should say (if no full body is provided)\n"
    "- \"date_range\": time filter for search/read, like \"last week\" or \"today\"\n\n"

    "Always return values in **pure JSON format** with double quotes and no explanations or markdown.\n\n"

    "Examples:\n\n"

    "User: 'Send an email to Alex about the demo on Friday'\n"
    "Output:\n"
    '{\n'
    '  "action": "send",\n'
    '  "params": {\n'
    '    "to": "Alex",\n'
    '    "subject": "Demo on Friday",\n'
    '    "query": "Inform Alex about the upcoming demo on Friday."\n'
    '  }\n'
    '}\n\n'

    "User: 'Reply to John's email with a thank you note'\n"
    "Output:\n"
    '{\n'
    '  "action": "reply",\n'
    '  "params": {\n'
    '    "sender": "John",\n'
    '    "query": "Thank you for your message.",\n'
    '    "message_id": "REQUIRED_FROM_SYSTEM_CONTEXT"\n'
    '  }\n'
    '}\n\n'

    "If any required details (like message_id) are missing, fill in what you can and use placeholder like default or leave them out.\n"
    "Do not include any text outside the JSON block."
)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                # Recommended to force JSON output if model supports it for stability
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content            
            # Use the clean method to parse JSON
            if content.startswith("```json"):
                content = content.replace("```json", "").strip()
            if content.endswith("```"):
                content = content[:-3].strip()
            return json.loads(content)
        except Exception as e:
            logging.error(f"Error parsing LLM response in Email Agent: {e}")
            # Return a structured error dict, not a conversational string
            return {"error": "JSON_PARSE_ERROR"}

    # CRITICAL: This method name is standardized for all Field Agents
    # -------------------- Main Contract Function --------------------

    def handle_query(self, query: str, context: Any = None) -> Dict[str, Any]:
        """
        Executes the email task. Returns the unified structured dictionary:
        {"status": str, "action": str, "context": Dict}.
        """
        logging.info(f"EmailAgent received query: {query}")
        
        # 1. 🎯 NEW: Contextual Retrieval Priority (Fix for Query 4)
        if query.startswith("RETRIEVE_BY_ID:"):
            return self._handle_retrieve_by_id(query) # Delegate to new handler

        # 2. Analyze the query to get the structured task (LLM PARSING)
        task = self._analyze_query_to_json(query) 
        
        if task.get("error"):
            # New Contract: ERROR
            return {"status": "ERROR", "action": "parse", "context": {"reason": f"LLM parsing failed: {task['error']}"}}
        
        action = task.get("action")
        params = task.get("params", {})
        
        # 3. Handle resumption logic (injecting user's answer into params)
        if context and isinstance(context, str) and not context.startswith(("RAW_DATA", "RAW_STATUS")):
            # If the context is a direct answer from the user (e.g., "sarah@example.com")
            if action in ["send", "reply"] and not params.get("to"):
                params["to"] = context 
            
            # Re-call the action handler with updated params
            # NOTE: We keep this simple for now; in a real system, the Director handles plan correction.
            return self._handle_action(action, params, context)
            
        # 4. Execute the action via the action handler
        result = self._handle_action(action, params, context)
        
        # 5. Final Contract Mapping (Mapping action result to the new contract)
        
        # If the result is a dict (standard), it should already be the new contract
        if isinstance(result, dict) and 'status' in result:
             return result
        
        # If result is a string, analyze it based on content (Legacy/Error Handling)
        if isinstance(result, str):
            if "Agent Error:" in result:
                # INCOMPLETE or FATAL_ERROR strings are caught here
                if "MISSING_DATA" in result or "MULTIPLE_CONTACTS" in result:
                    return {"status": "INCOMPLETE", "action": action, "context": {"reason": result}}
                else:
                    return {"status": "ERROR", "action": action, "context": {"reason": result}}
            
            # If it's a simple status string from a successful execution (e.g., "RAW_STATUS: EMAIL_SENT")
            if result.startswith("RAW_STATUS:"):
                 # SUCCESS PATH where action is complete, but no data is returned
                 return {"status": "COMPLETE", "action": action, "context": {"message": f"Success: {result.split(':')[-1].strip()}"}}

            # If it's an unhandled string, treat as raw data for fallback formatting
            return {"status": "COMPLETE", "action": action, "context": {"raw_data": result, "message": None}}

        # If result is complex (List/Dict of emails), treat as raw data.
        # Agent has NOT formatted it, so message is None.
        return {"status": "COMPLETE", "action": action, "context": {"raw_data": result, "message": None}}
    
    # -------------------- Action Dispatcher (Private) --------------------
    
    def _handle_action(self, action: str, params: Dict, context: Any = None) -> Any:
        
        if action == "read":
            # Direct the 'read' action to the raw data handler
            return self._handle_read_emails(params.get("max_results", 5), params.get("sender"))

        elif action == "send":
            return self._handle_send_email(params)
        
        elif action == "reply":
            return self._handle_reply_email(params)
        
        else:
            return f"Agent Error: UNKNOWN_ACTION; Action '{action}' not supported."

    # -------------------- Action Executors (Private) --------------------

    def _handle_read_emails(self, max_results: int, sender: Optional[str] = None) -> Any:
        """
        Fetches raw email data. 
        Returns List[Dict] containing ONLY metadata (token efficient).
        """
        try:
            if sender:
                emails = self.mail_tool.get_emails_from_sender(sender, max_results)
            else:
                emails = self.mail_tool.get_unread_emails(max_results)

            if not emails:
                return "RAW_DATA: NO_EMAILS_FOUND" # Handled by wrap in handle_query

            # 🎯 CRITICAL TOKEN EFFICIENCY FIX: Strip the body before returning raw data
            metadata_only_emails = []
            for email in emails:
                metadata_only_emails.append({
                    "id": email.get("id"),
                    "thread_id": email.get("thread_id"),
                    "subject": email.get("subject"),
                    "sender": email.get("sender"),
                    "date": email.get("date"),
                    # Explicitly omit the 'body' key
                })

            if not metadata_only_emails:
                # SUCCESS: NO CONTENT
                return {
                    "status": "COMPLETE", 
                    "action": "read", 
                    "context": {"message": "No new emails found matching the criteria.", "raw_data": []}
                }

            # Return the new COMPLETE contract (RAW_DATA provided, but message is None, 
            # forcing Director's final formatter LLM as a *formatter*)
            return {
                "status": "COMPLETE", 
                "action": "read", 
                # Raw list of emails (metadata only) - needs Director's final formatting
                "context": {"raw_data": metadata_only_emails, "message": None} 
            }
        
        except Exception as e:
            # FATAL_ERROR contract
            return {
                "status": "ERROR", 
                "action": "read", 
                "context": {"reason": f"MAIL_TOOL_FAILURE; Failed to read emails: {str(e)}"}
            }
        
    def _handle_send_email(self, params: Dict) -> str:
        """Handles sending, including contact resolution and error reporting."""
        to_name = params.get("to")
        email_context = params.get("query")
        subject = params.get("subject")
        
        if not to_name or not email_context:
            return "Agent Error: MISSING_DATA_REQUIRED; Recipient name or content is missing."

        to_email = to_name # Assume it's a raw email if '@' is present
        
        # Example of conversion of simple string returns to the new INCOMPLETE status
        if '@' not in to_name:
             contact_result = self._suggest_contacts(to_name)
             if contact_result.startswith("Agent Error: MULTIPLE_CONTACTS"):
                 return contact_result # INCOMPLETE status
             elif contact_result.startswith("Contact Error:"):
                 return f"Agent Error: MISSING_DATA_EMAIL_CONTACT; {to_name}" # INCOMPLETE status
             to_email = contact_result

        try:
            # 6. Compose the email (using hidden LLM)
            composed = self._compose_email(to=to_email, subject=subject, content_prompt=email_context)
            if not composed.get("success"):
                 return f"Agent Error: COMPOSE_FAILURE; {composed['error']}"

            # 7. EXECUTION: Send the email (Returns True or raises exception in pure tool)
            success = self.mail_tool.send_email(to=to_email, subject=composed["subject"], body=composed["body"])

            # Assuming mail_tool.send_email is now a pure executor that raises an exception on failure
            if success:
                 return f"RAW_STATUS: EMAIL_SENT; Recipient: {to_email}; Subject: {composed['subject']}"
            else:
                 # This path shouldn't happen if tool raises exception, but kept for robustness
                 return f"Agent Error: SEND_FAILURE; Failed to send email."

        except Exception as e:
             # Catch Tool exceptions (e.g., MailToolError/API failure)
             return f"Agent Error: SYSTEM_EXECUTION_ERROR; {str(e)}"

    # -------------------- Auxiliary LLM/Tool Methods (Private) --------------------

    def _compose_email(self, to: str, subject: Optional[str], content_prompt: str) -> Dict[str, Any]:
        """Composes the email body/subject using LLM, remaining internal to the agent."""
        # Removed the redundant subject generation logic from here, as the LLM in the body generation
        # is instructed to provide the subject in its JSON output.
        
        sender_name = self.sender_name or "Wingman"

        # We reuse the LLM logic from the old _generate_email_content, 
        # as it returned a structured JSON with subject and body, which is cleaner.
        return self._generate_email_content_json(to, content_prompt, subject)
    
    # Replaced the old complex compose_email and deleted _generate_email_content
    def _generate_email_content_json(self, to: str, context: str, subject: Optional[str] = None) -> Dict[str, Any]:
        """Generates email content using GPT, returning structured JSON."""
        # This function is kept private and acts as an internal LLM tool for the agent.
        try:
            messages = [
                {"role": "system", "content": f"""
                You are an email composer. Generate a professional email based on the given context.
                Current sender's name: {self.sender_name}
                
                IMPORTANT: Generate a JSON response with:
                "subject": "Appropriate subject line"
                "body": "Complete email body with greeting, clear message, and closing signed by {self.sender_name}"
                """},
                {"role": "user", "content": f"""
                To: {to}
                Context/Request: {context}
                Subject Hint: {subject if subject else 'Generate appropriate subject'}
                
                Please compose a suitable email based on this context. Return only the JSON object.
                """}
            ]

            completion = self.client.chat.completions.create(
                model="gpt-4o-mini", # Changed to mini for speed
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            content = json.loads(completion.choices[0].message.content)
            
            if not content.get("subject") or not content.get("body"):
                raise ValueError("LLM did not return required subject or body.")
            
            return {"subject": content["subject"], "body": content["body"], "success": True}
        
        except Exception as e:
            logging.error(f"Error generating email content JSON: {e}")
            return {"success": False, "error": str(e)}

    # -------------------- Tool Methods (Renamed/Simplified) --------------------

    def _suggest_contacts(self, partial_name: str) -> str:
        """Get contact suggestions based on partial name, returning only the resolved email or error string."""
        suggestions = self.mail_tool.get_email_suggestions(partial_name)
        
        if not suggestions:
            return f"Contact Error: No contacts found matching '{partial_name}'"
            
        if len(suggestions) > 1:
            # Structured error for Director to ask user to choose
            # The Director will be responsible for formatting this list for the user
            suggestion_list = "\n".join([f"- {name} <{email}>" for name, email in suggestions])
            return f"Agent Error: MULTIPLE_CONTACTS; Name: {partial_name}; Suggestions: {suggestion_list}"

        # Return the single resolved email address
        return suggestions[0][1]

    def _get_sender_name(self) -> str:
        """Get the sender's full name from Gmail profile."""
        try:
            profile = self.mail_tool.get_sender_profile()
            if profile and profile.get('name'):
                return profile['name']
            return "Wingman Assistant" 
        except Exception:
            return "Wingman Assistant"

    def _handle_retrieve_by_id(self, query: str) -> Dict[str, Any]:
        """Handles retrieval of a single mail body using the unique ID."""
        message_id = query.split(":")[1].strip()
        
        try:
            # 1. Get the full email object (assuming this includes the body)
            # NOTE: You MUST ensure your self.mail_tool has this method defined.
            full_mail_object = self.mail_tool.get_mail_body_by_id(message_id) 
            
            if not full_mail_object or not full_mail_object.get('body'):
                 return {
                    "status": "ERROR", 
                    "action": "retrieve_by_id", 
                    "context": {"reason": f"Mail ID {message_id} found, but body content is empty."}
                }
            
            # 2. Format the response locally (Distributed Formatting OPTIMIZATION)
            # We use a secondary LLM/internal method to format the body for conversational output.
            formatted_body = self._format_retrieved_body(full_mail_object)
            
            # 3. Return the new COMPLETE contract
            return {
                "status": "COMPLETE", 
                "action": "retrieve_by_id", 
                "context": {
                    "message": formatted_body, # Formatted for the user (OPTIMIZED PATH)
                    "raw_data": full_mail_object # Full object saved to memory
                }
            }

        except Exception as e:
            return {
                "status": "ERROR", 
                "action": "retrieve_by_id", 
                "context": {"reason": f"System error retrieving mail ID {message_id}: {str(e)}"}
            }
        
    def _format_retrieved_body(self, mail_object: Dict) -> str:
        """Internal LLM call to format the retrieved mail body for the user."""
        try:
            # We use an internal LLM call to structure the full mail body for the user.
            system_prompt = (
                "You are a concise email reader. Given the raw email data, extract the sender, subject, date, "
                "and the main content. Format the output cleanly for the user to read in a conversation. "
                "Do not add introductions. Use bullet points for metadata."
            )
            
            content_prompt = f"Raw Email Data:\n{json.dumps(mail_object, indent=2)}"
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content_prompt}
                ],
                temperature=0.1
            ).choices[0].message.content
            
            return response
            
        except Exception as e:
            # Fallback to a simple structured string if formatting LLM fails
            return (
                f"Body Content: {mail_object.get('body', 'Content not available.')}\n"
                f"Subject: {mail_object.get('subject', 'N/A')}"
            )
        
    