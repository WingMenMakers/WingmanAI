import json
import logging
from openai import OpenAI
from google.oauth2.credentials import Credentials
from wingman_logic.tools.WebsearchTool import WebSearchTool, WebSearchToolError
from typing import Dict, Any
from app.core.config import settings

class WebsearchAgent:
    """
    A Headless Executor Agent for web search. 
    Returns raw search data or structured error strings.
    """
    
    def __init__(self, api_key: str, credentials=None): 
        self.api_key = api_key
        self.credentials = credentials
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.search_tool = None
        
        try:
             # Pass the API key explicitly to the Tool's constructor
             self.search_tool = WebSearchTool(api_key=self.api_key) 
        except WebSearchToolError as e:
             logging.warning(f"Websearch Agent disabled: {e}")
             self.search_tool = None

    def handle_query(self, query: str, context: Any = None) -> Dict[str, Any]:
        """
        Handles search requests and returns the unified structured dictionary.
        {"status": str, "action": "search", "context": Any}.
        """
        action = "search"
        
        if not self.search_tool:
            context_error = "Agent Error: TOOL_UNAVAILABLE; Web search API is not configured."
            return {"status": "FATAL_ERROR: TOOL_FAIL", "action": action, "context": context_error}

        try:
            # 1. Attempt Quick Answer
            quick_result = self.search_tool.get_quick_answer(query)
            
            if quick_result.get("answer"):
                # Success: Return raw, structured quick answer data
                context_data = f"RAW_DATA: QUICK_ANSWER; Query: {query}; Answer: {quick_result['answer']}; Source: {quick_result['source']}"
                return {"status": "COMPLETE: RAW_DATA", "action": action, "context": context_data}
            
            # 2. Fall back to Detailed Search
            detailed_result = self.search_tool.get_detailed_search(query)
            
            if detailed_result.get("results"):
                # Success: Return raw, structured detailed results (JSON list/dict)
                # This complex data needs LLM formatting by the Director.
                return {"status": "COMPLETE: RAW_DATA", "action": action, "context": detailed_result}
            
            # 3. Total failure: No results found
            context_data = f"RAW_DATA: NO_RESULTS; Query: {query}"
            return {"status": "COMPLETE: RAW_DATA", "action": action, "context": context_data}
            
        except WebSearchToolError as e:
            # Catch Tool-level API errors and return a FATAL_ERROR status
            context_error = f"Agent Error: SEARCH_API_FAILURE; Reason: {e}"
            return {"status": "FATAL_ERROR: TOOL_FAIL", "action": action, "context": context_error}
            
        except Exception as e:
            context_error = f"Agent Error: SYSTEM_EXECUTION_ERROR; Reason: {str(e)}"
            return {"status": "FATAL_ERROR: SYSTEM_EXECUTION", "action": action, "context": context_error}
        