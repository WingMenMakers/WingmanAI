import os
import json
import logging
from openai import OpenAI
from Tools.WeatherTool import WeatherTool, WeatherApiError, LocationError # Assuming Tool exceptions are available
from typing import Dict, Any, Optional
from google.oauth2.credentials import Credentials 

class WeatherAgent:
    """
    A Smart-Headless Executor Agent for fetching raw weather data.
    Returns the unified structured dictionary for the Director.
    """
    
    def __init__(self, credentials: Credentials = None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # WeatherTool is assumed to be initialized correctly (no credential needed)
        try:
             self.weather_tool = WeatherTool()
        except Exception as e:
             logging.warning(f"Weather Tool failed to initialize: {e}")
             self.weather_tool = None # Tool may be unavailable if API key is missing

    def _check_location(self, user_query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine location intent.
        (Removed redundant LLM call from the original script)
        """
        messages = [
            {
                "role": "system",
                "content": """
                You are WingMan's location analyzer. Your task is to extract the intended location from the user's query.
                ... [rest of the prompt remains the same] ...
                """
            },
            {"role": "user", "content": user_query},
        ]

        try:
            # 🎯 FIX: Only one LLM call is needed for deterministic parsing
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1, 
                response_format={"type": "json_object"}
            )
            
            content = completion.choices[0].message.content.strip()
            data = json.loads(content)
            
            return {
                "current_location": data.get("location_type", "").lower() == "current",
                "location": data.get("location_name")
            }
        except Exception as e:
            logging.error(f"Location parsing failed: {e}")
            # If LLM parsing fails, default to current location (best guess)
            return {"current_location": True, "location": None}
            
    def handle_query(self, query: str, context: Any = None) -> Dict[str, Any]:
        """
        Executes the weather request and returns the unified structured dictionary.
        {"status": str, "action": "weather", "context": Any}.
        """
        action = "weather"
        
        if not self.weather_tool:
             context_error = "Agent Error: TOOL_UNAVAILABLE; Weather service is unavailable."
             return {"status": "FATAL_ERROR: TOOL_FAIL", "action": action, "context": context_error}
        
        try:
            # 1. Determine location type
            location_data = self._check_location(query)
            
            # 2. Get coordinates using WeatherTool
            location_coordinates = self.weather_tool.figure_out_location(location_data)
            
            if not location_coordinates:
                 # This is a failure to find the location, which can be recoverable by asking the user
                 context_error = "Agent Error: MISSING_DATA_WEATHER_LOCATION; Could not pinpoint the location."
                 # This triggers the Director's conversational loop
                 return {"status": "INCOMPLETE: MISSING_DATA", "action": action, "context": context_error}

            # 3. Get raw weather data using coordinates
            weather_data = self.weather_tool.get_weather(
                latitude=location_coordinates["latitude"],
                longitude=location_coordinates["longitude"]
            )
            
            # 4. Success: Return the RAW data (Tool is assumed to raise exceptions on failure)
            
            location_name = location_data.get("location") or "current location"
            
            # Complex data structure for Director formatting
            raw_output = {
                "source_query": query,
                "location": location_name,
                "weather_data": weather_data # Contains local_time, temp, humidity, etc.
            }
            
            return {"status": "COMPLETE: RAW_DATA", "action": action, "context": raw_output}

        except LocationError as e:
             # Catch specific Tool error for Location resolution fail
             context_error = f"Agent Error: LOCATION_API_FAILURE; Reason: {str(e)}"
             return {"status": "FATAL_ERROR: TOOL_FAIL", "action": action, "context": context_error}
        except WeatherApiError as e:
             # Catch specific Tool error for Weather API fail
             context_error = f"Agent Error: WEATHER_API_FAILURE; Reason: {str(e)}"
             return {"status": "FATAL_ERROR: TOOL_FAIL", "action": action, "context": context_error}
        except Exception as e:
             # Catch generic system or unexpected LLM exception
             context_error = f"Agent Error: SYSTEM_EXECUTION_ERROR; Reason: {str(e)}"
             return {"status": "FATAL_ERROR: SYSTEM_EXECUTION", "action": action, "context": context_error}
        