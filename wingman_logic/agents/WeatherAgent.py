import json
import logging
from openai import OpenAI
from wingman_logic.tools.WeatherTool import WeatherTool, WeatherApiError, LocationError # Assuming Tool exceptions are available
from typing import Dict, Any, Optional
from google.oauth2.credentials import Credentials 
from app.core.config import settings

class WeatherAgent:
    """
    A Smart-Headless Executor Agent for fetching raw weather data.
    Returns the unified structured dictionary for the Director.
    """
    
    def __init__(self, credentials: Credentials = None):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # WeatherTool is assumed to be initialized correctly (no credential needed)
        try:
             self.weather_tool = WeatherTool()
        except Exception as e:
             logging.warning(f"Weather Tool failed to initialize: {e}")
             self.weather_tool = None # Tool may be unavailable if API key is missing

    def _check_location(self, user_query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine location intent.
        """
        messages = [
            {
                "role": "system",
                "content": """
                You are WingMan's location analyzer. Your task is to extract the intended location from the user's query.
                
                ALWAYS return a single JSON object with these keys:
                "location_type": "current" OR "specific"
                "location_name": The exact city/area name mentioned (or null if location_type is "current").
                
                Example:
                User: "How's the weather in Seattle, Washington?"
                Output: {"location_type": "specific", "location_name": "Seattle, Washington"}
                
                User: "Is it going to rain today?"
                Output: {"location_type": "current", "location_name": null}
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
                # INCOMPLETE Status
                context_error = "Could not pinpoint the location. Please provide the city name."
                return {"status": "INCOMPLETE", "action": action, "context": {"reason": context_error}}
            
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
            
            return {"status": "COMPLETE", "action": action, "context": {"raw_data": raw_output}}
        
        except LocationError as e:
            # FATAL_ERROR contract
            context_error = f"Location API failure. Reason: {str(e)}"
            return {"status": "ERROR", "action": action, "context": {"reason": context_error}}
        
        except WeatherApiError as e:
            # FATAL_ERROR contract
            context_error = f"Weather API failure. Reason: {str(e)}"
            return {"status": "ERROR", "action": action, "context": {"reason": context_error}}
            
        except Exception as e:
            # Catch generic system error
            context_error = f"System execution error in Weather Agent. Reason: {str(e)}"
            return {"status": "ERROR", "action": action, "context": {"reason": context_error}}
        