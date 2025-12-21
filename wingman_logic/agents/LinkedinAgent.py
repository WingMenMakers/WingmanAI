import json
import logging
from openai import OpenAI
from wingman_logic.tools.LinkedinTool import LinkedInTool, LinkedInToolError # Import Tool and Error
from typing import Dict, Any 
import re 
from datetime import datetime, time as dt_time # Renaming time to dt_time to avoid conflict
from app.core.config import settings

class LinkedinAgent:
    
    def __init__(self, credentials: Dict[str, Any]): 
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
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
        
    # -------------------- Internal Post Generation --------------------

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
        
    # -------------------- Scheduling Handler --------------------
    
    def _handle_schedule(self, content: str, time_str: str) -> str:
        """
        Handles scheduling. Returns a RAW schedule confirmation for the Director.
        """
        if not content:
            return "Agent Error: MISSING_DATA_LINKEDIN_CONTENT; Action: schedule"
        
        if time_str in ["MISSING_TIME", None]:
            return "Agent Error: MISSING_DATA_LINKEDIN_TIME; Action: schedule"
        
        # Success: Return RAW status
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
            return {"status": "FATAL_ERROR", "action": action, "context": {"reason": context_error}}
            
        task = self._analyze_query_to_json(query)
        action = task.get("action", "parse_fail")

        if "error" in task:
            context_error = f"Agent Error: PARSE_ERROR; {task['error']}"
            return {"status": "FATAL_ERROR", "action": action, "context": {"reason": context_error}}

        topic = task.get("topic")
        content = task.get("content")
        time_str = task.get("time")

        try:
            agent_message = None
            raw_data = None

            # 1. Execute action logic
            if action == "generate":
                generated_content = self._generate_post_content(topic)
                raw_data = generated_content
                agent_message = f"Here is a draft for your LinkedIn post:\n\n{generated_content}"
                
            elif action == "post":
                if not content:
                    return {"status": "INCOMPLETE", "action": action, "context": {"reason": "Agent Error: MISSING_DATA_LINKEDIN_CONTENT"}}
                else:
                    self.linkedin_tool.post_content(content) 
                    agent_message = "Successfully posted to LinkedIn!"
                    raw_data = "POST_PUBLISHED"
                
            elif action == "generate_and_post":
                generated_content = self._generate_post_content(topic)
                self.linkedin_tool.post_content(generated_content)
                agent_message = f"Generated and posted to LinkedIn:\n\n{generated_content[:50]}..."
                raw_data = {"content": generated_content, "status": "PUBLISHED"}
                
            elif action == "schedule":
                raw_response = self._handle_schedule(content, time_str)
                if raw_response.startswith("Agent Error:"):
                     return {"status": "INCOMPLETE", "action": action, "context": {"reason": raw_response}}
                
                agent_message = f"Scheduled post for {time_str}."
                raw_data = raw_response
                
            elif action == "generate_and_schedule":
                generated_content = self._generate_post_content(topic)
                raw_response = self._handle_schedule(generated_content, time_str)
                if raw_response.startswith("Agent Error:"):
                     return {"status": "INCOMPLETE", "action": action, "context": {"reason": raw_response}}

                agent_message = f"Generated and scheduled post for {time_str}."
                raw_data = raw_response
                
            else:
                return {"status": "ERROR", "action": action, "context": {"reason": f"Agent Error: UNKNOWN_ACTION; Action '{action}' not supported."}}

            # 2. Final Output Mapping
            return {
                "status": "COMPLETE", 
                "action": action, 
                "context": {
                    "message": agent_message,
                    "raw_data": raw_data
                }
            }

        except LinkedInToolError as e:
            return {"status": "FATAL_ERROR", "action": action, "context": {"reason": f"Agent Error: LINKEDIN_API_FAILURE; {e}"}}
            
        except Exception as e:
            return {"status": "FATAL_ERROR", "action": action, "context": {"reason": f"Agent Error: SYSTEM_EXECUTION_ERROR; {str(e)}"}}