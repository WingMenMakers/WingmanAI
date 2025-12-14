import requests
import json
import logging
from typing import Dict, Any, Optional

# Custom Exception for Tool Errors
class LinkedInToolError(Exception):
    """Base exception for LinkedIn Tool failures."""
    pass

class LinkedInTool:
    def __init__(self, access_token: str, user_id: str):
        """Initialize the tool with required credentials."""
        if not access_token or not user_id:
            # Raise exception immediately; Agent handles the ValueError
            raise ValueError("LinkedIn access_token and user_id are required.")
            
        self.access_token = access_token
        self.user_id = user_id
        self.base_url = "https://api.linkedin.com/v2"

    def post_content(self, content: str) -> bool:
        """
        Post content directly to LinkedIn's UGC API.
        Returns True on success, raises LinkedInToolError on failure.
        """
        url = f"{self.base_url}/ugcPosts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json"
        }
        payload = {
            "author": f"urn:li:person:{self.user_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status() # Raises HTTPError for 4xx/5xx status codes
            
            # Success (status_code 201)
            return True
            
        except requests.exceptions.RequestException as e:
            # Catch request errors and convert to Tool Error
            error_msg = f"API request failed. Status: {e.response.status_code if e.response else 'N/A'}"
            try:
                error_details = e.response.json()
                error_msg += f". Details: {error_details.get('message', 'No details available')}"
            except:
                pass
            logging.error(f"LinkedIn post error: {error_msg}")
            raise LinkedInToolError(error_msg)