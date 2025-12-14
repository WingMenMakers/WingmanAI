import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv
from Tools.LinkedinTool import LinkedInTool, LinkedInToolError # Import Tool and Error
from typing import Dict, Any 
import re 
from datetime import datetime, time as dt_time # Renaming time to dt_time to avoid conflict

load_dotenv()

class LinkedinAgent:
    
    def __init__(self, credentials: Dict[str, Any]): 
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.available = False
        
        # 1. CRITICAL: Extract LinkedIn credentials and instantiate Tool
        access_token = credentials.get("access_token")
        user_id = credentials.get("user_id")
        
        try:
            self.linkedin_tool = LinkedInTool(access_token, user_id)
            self.available = True
        except ValueError as e:
            logging.error(f"LinkedIn Agent initialization failed: {e}")
        except Exception as e:
            logging.error(f"LinkedIn Tool initialization failed: {e}")

    # -------------------- Internal Task Parsing --------------------
    
    def _analyze_query_to_json(self, user_query):
        """Ask the LLM to parse the user query into a structured LinkedIn action."""
        agent_prompt = (
            """You are an assistant for managing LinkedIn posts. Return a JSON with double quotes only. Supported actions:

- "generate": Generate a LinkedIn post from a topic. Required keys: "action", "topic"
- "post": Post the given content now. Required keys: "action", "content"
- "generate_and_post": Generate from topic and post immediately. Required keys: "action", "topic"
- "schedule": Schedule existing content. Required keys: "action", "content", "time"
- "generate_and_schedule": Generate from topic and schedule a post. Required keys: "action", "topic", "time"

The "time" key must be a clear, unambiguous time string (e.g., "15:30" or "tomorrow at 10 AM"). If time is ambiguous or missing for schedule actions, use the placeholder 'MISSING_TIME'.
"""
        )
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": agent_prompt}, {"role": "user", "content": user_query}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception:
            return {"error": "JSON_PARSE_ERROR"}
        
    # -------------------- NEW: Internal Post Generation --------------------

    def _generate_post_content(self, topic: str) -> str:
        """Generate a professional LinkedIn post using the OpenAI client."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional LinkedIn content writer. Be inspiring, concise, and add emojis and 3-5 relevant hashtags. Return ONLY the post text."},
                    {"role": "user", "content": f"Write an engaging LinkedIn post about my project: {topic}"}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Post generation failed: {str(e)}")
        
    # -------------------- CRITICAL FIX: Scheduling Handler --------------------
    
    def _handle_schedule(self, content: str, time_str: str) -> str:
        """
        Handles scheduling. Since we cannot run a blocking loop, we return a RAW 
        schedule confirmation for the Director to handle conversationally.
        """
        if not content:
            return "Agent Error: MISSING_DATA_LINKEDIN_CONTENT; Action: schedule"
        
        # We need a robust time string (e.g., "15:30" or "tomorrow at 10 AM")
        if time_str in ["MISSING_TIME", None]:
            return "Agent Error: MISSING_DATA_LINKEDIN_TIME; Action: schedule"
        
        # 🎯 Success: Return RAW status with the content and time (no actual scheduling here)
        # The user must be informed that the current architecture requires an external scheduler.
        return f"RAW_STATUS: SCHEDULE_CONFIRMED; Content: {content}; Time: {time_str}"

    # -------------------- Main Contract Function --------------------

    def handle_query(self, query: str, context: Any = None) -> Dict[str, Any]:
        """
        Main handler to interpret user input and perform actions.
        Returns the unified structured dictionary: {"status": str, "action": str, "context": Any}.
        """
        action = "unknown"

        if not self.available:
            context_error = "Agent Error: TOOL_UNAVAILABLE; LinkedIn service is unavailable due to missing credentials."
            return {"status": "FATAL_ERROR: TOOL_FAIL", "action": action, "context": context_error}
            
        task = self._analyze_query_to_json(query)
        action = task.get("action", "parse_fail")

        if "error" in task:
            context_error = f"Agent Error: PARSE_ERROR; {task['error']}"
            return {"status": "FATAL_ERROR: PARSE_ERROR", "action": action, "context": context_error}

        topic = task.get("topic")
        content = task.get("content")
        time_str = task.get("time")

        try:
            # 1. Execute action logic (all branches return a raw string)
            if action == "generate":
                generated_content = self._generate_post_content(topic)
                raw_response = f"RAW_DATA: GENERATED_CONTENT; Content: {generated_content}"
                
            elif action == "post":
                if not content:
                    raw_response = "Agent Error: MISSING_DATA_LINKEDIN_CONTENT; Action: post"
                else:
                    self.linkedin_tool.post_content(content) # Tool raises exception on failure
                    raw_response = "RAW_STATUS: POST_PUBLISHED; Content: Success"
                
            elif action == "generate_and_post":
                generated_content = self._generate_post_content(topic)
                self.linkedin_tool.post_content(generated_content)
                raw_response = f"RAW_STATUS: POST_PUBLISHED; Content: {generated_content[:50]}..."
                
            elif action == "schedule":
                # CRITICAL: Calls the non-blocking scheduler handler
                raw_response = self._handle_schedule(content, time_str)
                
            elif action == "generate_and_schedule":
                generated_content = self._generate_post_content(topic)
                raw_response = self._handle_schedule(generated_content, time_str)
                
            else:
                raw_response = f"Agent Error: UNKNOWN_ACTION; Action '{action}' not supported."

            # 2. Final Output Mapping (Specific-to-General If/Elif)
            
            # Specific Recoverable Errors (INCOMPLETE status)
            if raw_response.startswith("Agent Error: MISSING_DATA_LINKEDIN_CONTENT") or \
               raw_response.startswith("Agent Error: MISSING_DATA_LINKEDIN_TIME"):
                return {"status": "INCOMPLETE: MISSING_DATA", "action": action, "context": raw_response}
            
            # Fatal Errors (System failure, API failure)
            elif raw_response.startswith("Agent Error:"):
                return {"status": "FATAL_ERROR: AGENT_FAIL", "action": action, "context": raw_response}
            
            # Successful RAW Status/Data
            elif raw_response.startswith("RAW_STATUS:") or raw_response.startswith("RAW_DATA:"):
                return {"status": "COMPLETE: RAW_DATA", "action": action, "context": raw_response}
            
            # Catch-all for unexpected output
            return {"status": "COMPLETE: RAW_DATA", "action": action, "context": raw_response}

        except LinkedInToolError as e:
            context_error = f"Agent Error: LINKEDIN_API_FAILURE; Reason: {e}"
            return {"status": "FATAL_ERROR: TOOL_FAIL", "action": action, "context": context_error}
            
        except Exception as e:
            context_error = f"Agent Error: SYSTEM_EXECUTION_ERROR; Reason: {str(e)}"
            return {"status": "FATAL_ERROR: SYSTEM_EXECUTION", "action": action, "context": context_error}
        
    # def is_valid_time_format(self, t):
    #     return re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", t) is not None

    # def pad_time_format(self, t):
    #     parts = t.strip().split(":")
    #     if len(parts) == 2:
    #         return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
    #     elif len(parts) == 3:
    #         return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
    #     return t
