import json
import logging
from app.core.config import settings
from openai import OpenAI
from google.oauth2.credentials import Credentials
from wingman_logic.tools.DocTool import DocTool, DocToolError
from typing import Dict, Any, Optional

class DocAgent:
    REQUIRED_SCOPE = "https://www.googleapis.com/auth/documents"

    def __init__(self, credentials: Credentials):
        self.credentials = credentials
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.DocTool = DocTool(credentials=credentials)
        self.available = True

    # -------------------- Internal Task Parsing --------------------

    def _analyze_query_to_json(self, user_query):
        """Ask ChatGPT to convert natural language into structured JSON commands."""
        system_prompt = (
            """"You are an AI assistant that helps users manage Google Docs files.
Always respond in **pure JSON format**, using double quotes and without any explanatory text.
Your job is to interpret the user's intent and respond in **pure JSON format only**, with double quotes for all keys and values. Do not include any explanations or extra text.

Supported actions and required keys:

1. "create": Create a new Google Doc.
   Required keys: "action", "file_name", "initial_content"
   - If the file_name is not mentioned, take it as New File by default. And the "initial_content" value is optional.

2. "retrieve": Retrieve a document by its name or ID.
   Required keys: "action", "file_name"
   - If the file_name is not mentioned, try to make it out from the context of the user query.

3. "add_text": Add text to an existing document.
   Required keys: "action", "file_name", "content"

4. "update": Update or replace specific text in a document.
   Required keys: "action", "file_name", "new_text"
   - If the file_name and/or new_text is not mentioned, try to make it out from the context of the user query.

5. "delete": Delete a document by name or ID.
   Required keys: "action", "file_name"
   - If the file_name is not mentioned, try to make it out from the context of the user query.

6. "summarize": Generate a summary of a document’s content.
   Required keys: "action", "file_name"
   - If the file_name is not mentioned, try to make it out from the context of the user query.

Examples of user queries and corresponding outputs:

- **"Create a document titled Project Plan and add the intro"**  
  → `{ "action": "create", "file_name": "Project Plan", "initial_content": "Add the intro" }`

- **"Summarize the document called Meeting Notes"**  
  → `{ "action": "summarize", "file_name": "Meeting Notes" }`

- **"Add this to the beginning of the file: Our mission is clear."**  
  → `{ "action": "add_text", "file_name": "Company Vision", "content": "Our mission is clear.", "location": "start" }`

If a query lacks enough detail, ask for clarification by responding with a JSON object:
`{ "error": "Missing [field_name]. Please provide more information." }'
Except if a file name is not found leave the file_name field empty or use a placeholder like 'MISSING_FILE_NAME'."
"""
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_query}],
                response_format={"type": "json_object"}
            ).choices[0].message.content
            
            # Simplified JSON cleaning/loading
            content = response.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logging.error(f"DocAgent parse error: {e}")
            return {"error": "JSON_PARSE_ERROR"}

    # -------------------- NEW: Internal Ambiguity Resolver --------------------

    def _resolve_file_ambiguity(self, ambiguous_name: str) -> str:
        """
        Tries to resolve an ambiguous or partial file name using the LLM against recent docs.
        Returns: The exact resolved file name (str) OR a structured Agent Error string.
        """
        try:
            ten_docs = self.DocTool.get_recent_google_docs()
            doc_names = [doc["name"] for doc in ten_docs]
            
            # Quick check for exact match or early exit
            if ambiguous_name in doc_names:
                 return ambiguous_name
            if not ten_docs:
                 return f"Agent Error: FILE_NOT_FOUND; Target: {ambiguous_name}; Reason: No recent files available."

            doc_list_str = "\n".join([f"- {doc['name']}" for doc in ten_docs])
            
            # Use LLM for deterministic fuzzy matching (Smart-Headless logic)
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a deterministic file resolver. Given the user's ambiguous target, find the EXACT NAME of the best-matching document from the list. If there is ANY ambiguity or no clear match, return ONLY the specific phrase 'AMBIGUOUS_MATCH'."},
                    {"role": "user", "content": f"Recent documents:\n{doc_list_str}\n\nThe user is referring to the document named: '{ambiguous_name}'"}
                ],
                temperature=0.1
            ).choices[0].message.content.strip()

            if response == "AMBIGUOUS_MATCH":
                 # Trigger Director interruption for user choice
                 return f"Agent Error: AMBIGUOUS_FILE_MATCH; Target: {ambiguous_name}; Recent files: {doc_list_str}"
            
            # Success: Return the resolved name
            return response

        except Exception as e:
            logging.error(f"File ambiguity resolution failed: {e}")
            return f"Agent Error: SYSTEM_EXECUTION_ERROR; File resolution failed: {str(e)}"
        
    # -------------------- NEW: Action Handlers (Replacing handle_action) --------------------
    
    def _get_doc_id_resolved(self, file_name: str) -> tuple[str, str]:
        """
        Resolves file name to ID, handling ambiguity if necessary.
        Raises ValueError with a structured error string if resolution fails.
        """
        if not file_name or file_name == "MISSING_FILE_NAME":
             # This triggers INCOMPLETE status
             raise ValueError("Agent Error: MISSING_DATA_DOC_FILE_NAME; Target: N/A")

        resolved_name_or_error = self._resolve_file_ambiguity(file_name)
        
        if resolved_name_or_error.startswith("Agent Error:"):
             # Ambiguity or System Error detected during resolution
             raise ValueError(resolved_name_or_error) # Director will catch this
        
        resolved_name = resolved_name_or_error
        
        doc_id = self.DocTool.resolve_file_name_to_id(resolved_name)
        
        if not doc_id:
             # File not found after resolution
             raise ValueError(f"Agent Error: FILE_NOT_FOUND; Target: {resolved_name}")
             
        return doc_id, resolved_name

    # -------------------- Dedicated Action Handlers --------------------

    def _handle_create(self, params: Dict) -> str:
        file_name = params.get("file_name", "New Document")
        content = params.get("initial_content", "")
        
        try:
            doc_data = self.DocTool.create_google_doc(title=file_name, initial_content=content)
            # Success: Return RAW status string
            return f"RAW_STATUS: DOC_CREATED; ID: {doc_data['id']}; Title: {doc_data['title']}; Link: {doc_data['link']}"
        except DocToolError as e:
            return f"Agent Error: DOC_TOOL_FAILURE; Failed to create file: {e}"

    def _handle_retrieve(self, params: Dict) -> str:
        file_name = params.get("file_name")
        
        try:
            doc_id, resolved_name = self._get_doc_id_resolved(file_name)
            content = self.DocTool.get_google_doc_content(doc_id)
            
            # Success: Return raw content string
            return f"RAW_DATA: DOC_CONTENT; Title: {resolved_name}; Content: {content}"
            
        except DocToolError as e:
            return f"Agent Error: DOC_TOOL_FAILURE; Failed to retrieve file content: {e}"
        except ValueError as e:
            return str(e) # Pass through ValueError (INCOMPLETE/NOT_FOUND)

    def _handle_add_text(self, params: Dict) -> str:
        file_name = params.get("file_name")
        content = params.get("content")

        if not content:
            return "Agent Error: MISSING_DATA_DOC_CONTENT; Action: add_text"
        
        try:
            doc_id, resolved_name = self._get_doc_id_resolved(file_name)
            location = params.get("location", "end") 
            
            self.DocTool.add_to_google_doc(doc_id, content, location=location)
            
            # Success: Return RAW status string
            return f"RAW_STATUS: DOC_TEXT_ADDED; Title: {resolved_name}; Location: {location}"
            
        except DocToolError as e:
            return f"Agent Error: DOC_TOOL_FAILURE; Failed to add text: {e}"
        except ValueError as e:
            return str(e)

    def _handle_update(self, params: Dict) -> str:
        file_name = params.get("file_name")
        new_text = params.get("new_text")

        if not new_text:
            return "Agent Error: MISSING_DATA_DOC_NEW_TEXT; Action: update"

        try:
            doc_id, resolved_name = self._get_doc_id_resolved(file_name)
            
            # 1. Retrieve current content
            old_text = self.DocTool.get_google_doc_content(doc_id)

            # 2. Internal LLM Call: Merge content (Smart-Headless functionality)
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a content merger. Integrate the 'New' content into the 'Old' document, preserving structure."},
                    {"role": "user", "content": f"Old Document Content:\n{old_text}\nNew Content/Instructions:\n{new_text}"}
                ]
            )
            updated_text = response.choices[0].message.content
            
            # 3. Overwrite document with merged content
            self.DocTool.edit_google_doc(doc_id, updated_text)
            
            # Success: Return RAW status string
            return f"RAW_STATUS: DOC_UPDATED; Title: {resolved_name}"
            
        except DocToolError as e:
            return f"Agent Error: DOC_TOOL_FAILURE; Failed to update document: {e}"
        except ValueError as e:
            return str(e)

    def _handle_delete(self, params: Dict) -> str:
        file_name = params.get("file_name")
        
        try:
            doc_id, resolved_name = self._get_doc_id_resolved(file_name)
            
            self.DocTool.delete_google_doc(doc_id)
            
            # Success: Return RAW status string
            return f"RAW_STATUS: DOC_DELETED; Title: {resolved_name}"
            
        except DocToolError as e:
            return f"Agent Error: DOC_TOOL_FAILURE; Failed to delete file: {e}"
        except ValueError as e:
            return str(e)

    def _handle_summarize(self, params: Dict) -> str:
        file_name = params.get("file_name")
        
        try:
            doc_id, resolved_name = self._get_doc_id_resolved(file_name)
            content = self.DocTool.get_google_doc_content(doc_id)
            
            # Internal LLM Call for summarization
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarize the document concisely. Include key points and headings if possible."},
                    {"role": "user", "content": content}
                ]
            )
            summary = response.choices[0].message.content
            
            # Success: Return the RAW summary string
            return f"RAW_DATA: DOC_SUMMARY; Title: {resolved_name}; Summary: {summary}"
            
        except DocToolError as e:
            return f"Agent Error: DOC_TOOL_FAILURE; Failed to summarize file: {e}"
        except ValueError as e:
            return str(e)

    # -------------------- Main Contract Function --------------------

    def handle_query(self, query: str, context: Any = None) -> Dict[str, Any]:
        """
        Executes the Doc task. Returns the unified structured dictionary:
        {"status": str, "action": str, "context": Any}.
        """
        logging.info(f"Doc Agent received query: {query}")
        action = "unknown"
        
        try:
            # 1. Analyze the query
            task = self._analyze_query_to_json(query)
            action = task.get("action", "parse_fail")
            
            if task.get("error"):
                 # Parser error is unrecoverable by the Agent
                 return {"status": "FATAL_ERROR: PARSE_ERROR", "action": action, "context": f"LLM parsing failed: {task['error']}"}

            # 2. Dispatch to dedicated handler
            if action == "create":
                response = self._handle_create(task)
            elif action == "retrieve":
                response = self._handle_retrieve(task)
            elif action == "summarize":
                response = self._handle_summarize(task)
            elif action == "add_text":
                response = self._handle_add_text(task)
            elif action == "update":
                response = self._handle_update(task)
            elif action == "delete":
                response = self._handle_delete(task)
            else:
                response = f"Agent Error: UNKNOWN_ACTION; Action '{action}' not supported."

            # 3. Final Output Wrapping
            # All successful and recoverable failure paths return a string from the handlers.
            
            if isinstance(response, str):
            
                # Specific Recoverable Errors (INCOMPLETE status)
                if response.startswith("Agent Error: MISSING_DATA") or response.startswith("Agent Error: AMBIGUOUS_FILE_MATCH"):
                    # Extract the message details for the Director
                    return {"status": "INCOMPLETE", "action": action, "context": {"reason": response}}
                
                # Fatal Errors
                elif response.startswith("Agent Error:"):
                    # Catch all remaining Fatal Errors
                    return {"status": "ERROR", "action": action, "context": {"reason": response}}
                
                # Successful RAW Status/Data
                elif response.startswith("RAW_STATUS:") or response.startswith("RAW_DATA:"):
                    # Success, but needs formatting (message: None)
                    return {"status": "COMPLETE", "action": action, "context": {"raw_data": response}}
                
                else:
                    # Catch-all for unexpected successful strings (treat as raw data)
                    return {"status": "COMPLETE", "action": action, "context": {"raw_data": response}}
            
            # If the response is a complex object (shouldn't happen here, but defaults to complete)
            return {"status": "COMPLETE", "action": action, "context": {"raw_data": response}}

        except Exception as e:
            # Catch any unexpected Python exceptions that bubble up
            return {"status": "ERROR", "action": action, "context": {"reason": str(e)}}
        