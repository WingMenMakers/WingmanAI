import json
import logging
from openai import OpenAI
from datetime import datetime
from google.oauth2.credentials import Credentials 
from wingman_logic.tools.CalendarTool import GoogleCalendarTool 
from typing import Dict, Any, List, Optional
from app.core.config import settings

class CalendarAgent:
    # 1. CRITICAL: Accept credentials object
    def __init__(self, credentials: Credentials):
        self.credentials = credentials
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.today_date = datetime.today().strftime("%Y-%m-%d")
        self.CalendarTool = GoogleCalendarTool(credentials=credentials)

    # -------------------- LLM Task Parsing (Internal Tool) --------------------
    
    def _analyze_query_to_json(self, user_query: str) -> Dict[str, Any]:
        """Uses LLM to parse the user query into a structured action/params JSON."""
        system_prompt = (
            f"You are an AI assistant that extracts calendar action details. Today's date is {self.today_date}. "
            "Interpret all dates relative to this date and output them in ISO format (YYYY-MM-DDTHH:MM:SS).\n\n"
    
            "ALWAYS respond in **pure JSON format** with exactly the following keys, filling with null or a specific placeholder if data is missing:\n"
            '{\n'
            '  "action": "create"|"update"|"delete"|"check"|"extract",\n'
            '  "event_name": "...",\n'
            '   "event_id": "..." (The extracted Event ID, if present in the query/context)\n' # <-- NEW ID FIELD
            '  "start_time": "YYYY-MM-DDTHH:MM:SS" (or null),\n'
            '  "end_time": "YYYY-MM-DDTHH:MM:SS" (or null),\n'
            '  "query_context": "..."\n'
            '}\n\n'

            "RULES:\n"
            "- If an end_time is missing for 'create', set it to **one hour** after the start_time.\n"
            "- If start_time or end_time is ambiguous or missing for 'create', use the placeholder 'MISSING_TIME'.\n"
            "- If the event_name is missing for 'update' or 'delete', use the placeholder 'MISSING_EVENT_NAME'."
            "- If the query contains 'ID:' followed by an alphanumeric string, extract it and place it directly into the 'event_id' field. This overrides all other event identification methods."
            )
       
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                response_format={"type": "json_object"}
            )
            message = response.choices[0].message.content.strip()
            return json.loads(message)
        except Exception as e:
            logging.error(f"Calendar LLM parse error: {e}")
            return {"error": "JSON_PARSE_ERROR"}
        
    # -------------------- NEW: Internal Ambiguity Resolver --------------------

    def _resolve_ambiguous_event(self, query: str, start: str, end: str) -> str:
        """
        Uses an internal LLM call to resolve a generic query (e.g., 'the meeting') 
        against a list of events in a time window.
        
        Returns: 
        - The exact event name (str) if one is found, OR
        - A structured error string if multiple events are plausible or none are found.
        """
        try:
            # 1. Fetch all events in the provided window (today/this week/etc.)
            existing_events = self.CalendarTool.extract_schedule(start, end)
            
            if not existing_events:
                return f"Agent Error: EVENT_NOT_FOUND; Target: Ambiguous; Events: None Found in window {start} to {end}."
            
            # Format raw events into a simple list for the internal LLM
            event_summaries = []
            for event in existing_events:
                event_summaries.append(f"'{event.get('summary', 'No Name')}' at {event.get('start', 'N/A')}")
            
            event_list_str = "\n".join(event_summaries)
            
            # 2. Internal LLM Guess (Micro-Correction)
            messages = [
                {"role": "system", "content": f"""
                You are a deterministic event resolver. The user wants to act on an event vaguely described as '{query}'.
                The available events in the target time window are:
                {event_list_str}
                
                Analyze the user's intent: '{query}' against the available events.
                
                RULES:
                1. If exactly **ONE** event clearly matches the time/description, return ONLY that exact event's **summary** (event name).
                2. If **MULTIPLE** events are plausible matches, or if no event clearly matches, return the specific string 'AMBIGUOUS_MATCH'.
                3. DO NOT return any conversational text, explanations, or JSON.
                """},
                {"role": "user", "content": f"Resolve the event name for the query: '{query}'."}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1 # Low temp for deterministic output
            ).choices[0].message.content.strip()
            
            if response == "AMBIGUOUS_MATCH":
                # 3. Trigger Director interruption if ambiguity remains
                return f"Agent Error: AMBIGUOUS_EVENT_MATCH; Query: {query}; Events: {json.dumps(existing_events)}"
            
            # 4. Success: Return the resolved event name
            return response
            
        except Exception as e:
            logging.error(f"Internal event resolution failed: {e}")
            return f"Agent Error: SYSTEM_EXECUTION_ERROR; Internal resolution failed: {str(e)}"

    def _resolve_temporal_dependency(self, dependency_string: str) -> str:
        """
    Uses an internal LLM call to resolve a time dependency string 
    (e.g., 'after my meeting at 4') into a precise ISO timestamp.
    
    Returns: The calculated ISO 8601 string, or a structured error signal.
    """
        try:
            # 1. Fetch current schedule to provide context for the LLM
            # We assume dependency usually relates to today or the immediate future.
            schedule_raw = self.CalendarTool.extract_schedule(self.today_date, None) 
        
            messages = [
            {"role": "system", "content": f"""
            You are a temporal dependency calculator. Your task is to calculate a precise start time 
            based on a user dependency relative to their current schedule.
            
            Today's Date: {self.today_date}.
            
            Current Schedule (for context): {json.dumps(schedule_raw)}
            
            RULES:
            1. Calculate the final start time based on the dependency string and the schedule.
            2. Return ONLY the final calculated time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
            3. If the dependency cannot be resolved (e.g., 'my meeting' is ambiguous or not found), 
               return the specific string 'RESOLUTION_FAILURE'.
            """},
            {"role": "user", "content": f"Calculate the start time for the event: '{dependency_string}'."}
            ]
        
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1
            ).choices[0].message.content.strip()
        
            if response == "RESOLUTION_FAILURE":
                return f"Agent Error: TEMPORAL_RESOLUTION_FAILURE; Dependency: {dependency_string}"
        
            # Success: Return the calculated time
            return response
        
        except Exception as e:
            logging.error(f"Temporal resolution failed: {e}")
            return f"Agent Error: SYSTEM_EXECUTION_ERROR; Temporal resolution failed: {str(e)}"
        
    # agents/CalendarAgent.py (Adding the centralized resolver)

    def _resolve_internal_errors(self, task: Dict[str, Any], query: str) -> Dict[str, Any] | str:
        """
        Central function to attempt internal resolution for ambiguous data (time or event name).
    
        :param task: The structured task dictionary from _analyze_query_to_json.
        :param query: The original user query context.
        :return: The corrected task dictionary OR a structured Agent Error string.
        """
        action = task.get("action")
        event_name = task.get("event_name")
        start_time = task.get("start_time")
        end_time = task.get("end_time")
        query_context = task.get("query_context", query)

        # --- Case 1: Ambiguous or Missing Event Name (for update/delete) ---
        if action in ["update", "delete"] and event_name == "MISSING_EVENT_NAME":
            if start_time and end_time:
                # We have a time range but a generic name (e.g., "delete the meeting today").
                resolved_name = self._resolve_ambiguous_event(query_context, start_time, end_time)
            
                if resolved_name.startswith("Agent Error:"):
                    # Still ambiguous or not found -> return error to Director
                    return resolved_name 
            
                # Internal resolution succeeded: Update the task and return it.
                task['event_name'] = resolved_name
                return task
            else:
                # Cannot proceed without a name OR a time range
                return f"Agent Error: MISSING_DATA_CALENDAR_EVENT; Original Query: {query}"

        # --- Case 2: Temporal Dependency (for create) ---
        if action == "create" and start_time and start_time.startswith("DEPENDENT:"):
            dependency_string = start_time.split("DEPENDENT: ")[1]
        
            resolved_time = self._resolve_temporal_dependency(dependency_string)
        
            if resolved_time.startswith("Agent Error:"):
                # Failed to resolve dependency (e.g., "my meeting" is ambiguous) -> return error to Director
                return resolved_time
        
            # Internal resolution succeeded: Update the task
            task['start_time'] = resolved_time
        
            # Also ensure end_time is calculated if it was null
            if not end_time:
                task['end_time'] = self.CalendarTool.calculate_one_hour_end_time(resolved_time)
        
            return task

        # --- Default: No internal correction needed or possible ---
        return task
    
    # -------------------- Main Contract Function --------------------

    def handle_query(self, query: str, context: Any = None) -> Dict[str, Any]:
        """
        Executes the calendar task. Returns the unified structured dictionary:
        {"status": str, "action": str, "context": Any}.
        """
        logging.info(f"Calendar Agent received query: {query}")
        
        # 1. Analyze the query
        task = self._analyze_query_to_json(query)
        action = task.get("action", "unknown")

        if task.get("error"):
            return {"status": "FATAL_ERROR: PARSE_ERROR", "action": action, "context": f"LLM parsing failed: {task['error']}"}
        
        # 2. Handle Resumption Logic (User answered an interruption)
        if context and isinstance(context, str) and not context.startswith(("RAW_DATA", "RAW_STATUS")):
            # If the context is a direct answer, we assume the user is resolving an ambiguity (event name or time)
            # This logic needs to be complex and depends on what the Director stored. 
            # For now, we rely on the Director's Planner to create a corrected Plan B.
            # If the Director re-calls this agent with the *answer* as context, we assume the answer 
            # should be substituted into the next step of the original plan (handled by Director's Plan B).
            # We skip internal resolution here and rely on the Planner's re-generated query.
            pass
        
        # 3. Attempt Internal Error Resolution/Correction (Smart-Headless Logic)
        resolved_task_or_error = self._resolve_internal_errors(task, query)
    
        if isinstance(resolved_task_or_error, str):
            # --- FIX 2A: Standardize Resolver Failures ---
            
            # AMBIGUOUS/TEMPORAL FAILURE -> INCOMPLETE (recoverable)
            if resolved_task_or_error.startswith("Agent Error: AMBIGUOUS_EVENT_MATCH") or \
               resolved_task_or_error.startswith("Agent Error: TEMPORAL_RESOLUTION_FAILURE") or \
               resolved_task_or_error.startswith("Agent Error: MISSING_DATA"):
                
                return {"status": "INCOMPLETE", "action": action, "context": {"reason": resolved_task_or_error}}
            
            # System/Resolver Failures -> ERROR (fatal)
            return {"status": "ERROR", "action": action, "context": {"reason": resolved_task_or_error}}

        # Correction succeeded or none was needed. Use the updated task dictionary.
        task = resolved_task_or_error
        
        action = task.get("action")
        event_name = task.get("event_name")
        start_time = task.get("start_time")
        end_time = task.get("end_time")

        # 4. Final check for critical missing data *before* execution (Should be mostly handled by resolver)
        if action == "create" and (start_time == "MISSING_TIME" or not start_time):
             # Planner failed and resolver couldn't fix it.
            reason = f"Agent Error: MISSING_DATA_CALENDAR_TIME; Event name: {event_name or 'N/A'}"
            return {"status": "INCOMPLETE", "action": action, "context": {"reason": reason}}
        
        # 5. Execute the Action
        try:
            if action == "create":
                response = self.CalendarTool.create_event(event_name, start_time, end_time)
                
                if response and "id" in response:
                    # --- NEW: Filter the response to keep only high-signal keys ---
                    filtered_raw_data = {
                        "type": "CalendarEvent",
                        "id": response.get("id"),
                        "summary": response.get("summary"),
                        "htmlLink": response.get("htmlLink"),
                        "start": response.get("start"),
                        "end": response.get("end")
                    }
                    
                    # --- Store the filtered data for memory injection ---
                    agent_message = f"Successfully scheduled '{event_name}' for {start_time}. Event ID: {response['id']}"

                    return {
                        "status": "COMPLETE", 
                        "action": action, 
                        "context": {
                            "message": agent_message,
                            "raw_data": filtered_raw_data # <-- NOW A CLEAN, CONCISE DICT
                        }
                    }
                else:
                    raise Exception(f"Tool failed to return ID: {response}")

            elif action == "update":
                update_result = self.CalendarTool.update_event(event_name, start_time, end_time)
                
                if update_result and "id" in update_result:
                    agent_message = f"Meeting '{event_name}' updated to start at {start_time}."
                    return {"status": "COMPLETE", "action": action, "context": {"message": agent_message, "raw_data": update_result}}
                
                # NOT_FOUND (unambiguous, so treat as INCOMPLETE/recoverable by asking user)
                reason = f"Agent Error: EVENT_NOT_FOUND; Target: {event_name}; Query: {query}"
                return {"status": "INCOMPLETE", "action": action, "context": {"reason": reason}}

            elif action == "delete":
                delete_result = self.CalendarTool.delete_event(event_name)

                if delete_result is True:
                    agent_message = f"Meeting '{event_name}' successfully deleted."
                    return {"status": "COMPLETE", "action": action, "context": {"message": agent_message}}
                
                # NOT_FOUND (INCOMPLETE)
                reason = f"Agent Error: EVENT_NOT_FOUND; Target: {event_name}; Query: {query}"
                return {"status": "INCOMPLETE", "action": action, "context": {"reason": reason}}
            
            elif action == "extract" or action == "check":
                # Ensure start/end time are present (safeguard)
                if not start_time or not end_time:
                    context = f"Agent Error: MISSING_DATA_CALENDAR_RANGE; Start/end time missing for {action}."
                    return {"status": "INCOMPLETE: MISSING_DATA", "action": action, "context": context}
                
                events_list = self.CalendarTool.extract_schedule(start_time, end_time)
                
                if not events_list:
                    return {"status": "COMPLETE", "action": action, "context": {"message": "No events found in that time range."}}
                
                # Success: Return raw event list (COMPLEX DATA - Director formats)
                return {"status": "COMPLETE", "action": action, "context": {"raw_data": events_list}}

            else:
                return {"status": "ERROR", "action": action, "context": {"reason": f"Action '{action}' not supported."}}

        except Exception as e:
            # FATAL TOOL/SYSTEM FAILURES
            return {"status": "ERROR", "action": action, "context": {"reason": f"CalendarTool failed: {str(e)}"}}
        