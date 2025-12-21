import os
from typing import Dict, List, Optional, Any
import requests
from dotenv import load_dotenv
import json
import logging

load_dotenv()

class WebSearchToolError(Exception):
    """Base exception for WebSearchTool failures."""
    pass

class WebSearchTool:
    def __init__(self, api_key: str):
        
        # 1. Use the API key passed from the WebsearchAgent (which gets it from settings.py)
        self.api_key = api_key
        
        if not self.api_key:
            # If the Director did not pass the key (shouldn't happen now), or the key is empty
            # Raise a clear error that the Director can catch and log.
            # We change the error message to reflect the new configuration source.
            raise WebSearchToolError("TAVILY API key is missing from environment variables (.env). Web search disabled.")
            
        self.base_url = "https://api.tavily.com/search"

    def search(self, query: str, search_depth: str = "basic") -> Dict[str, Any]:
        """
        Perform a web search using Tavily API. 
        Returns raw response dict, raises WebSearchToolError on failure.
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "query": query,
                "search_depth": search_depth,
                "include_images": False,
                "include_answer": True,
                "max_results": 5,
                "api_key": self.api_key
            }
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=15)
            
            # Raise exceptions for 4xx/5xx status codes
            response.raise_for_status() 
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            # Catch API/Network errors and re-raise as our custom error
            error_msg = f"API request failed with status {e.response.status_code if e.response else 'N/A'}"
            logging.error(f"Tavily API error: {error_msg}. Response: {e.response.text if e.response else 'None'}")
            raise WebSearchToolError(error_msg)
        except Exception as e:
            raise WebSearchToolError(f"Unexpected search error: {str(e)}")

    def get_quick_answer(self, query: str) -> Dict[str, Any]:
        """Get a quick answer using basic search. Returns structured dict."""
        result = self.search(query, search_depth="basic")
        
        # Consolidate answer extraction
        answer = result.get("answer")
        source = result.get("results", [{}])[0].get("url", "Unknown source")
        
        if answer:
            return {"answer": answer, "source": source}
        
        # If no direct answer, return the snippet of the first result as the answer
        snippet_answer = result.get("results", [{}])[0].get("snippet")
        if snippet_answer:
            return {"answer": snippet_answer, "source": source}

        # If still nothing, let the Agent handle the lack of data
        return {"answer": None, "source": None}

    def get_detailed_search(self, query: str) -> Dict[str, Any]:
        """Perform a detailed search for complex queries. Returns structured dict."""
        result = self.search(query, search_depth="deep")
        
        if result.get("results"):
            return {
                "results": result["results"], # Raw list of result dicts
                "answer": result.get("answer"),
                "query": query
            }
        
        return {"results": [], "answer": None, "query": query}