import logging
from typing import Dict, Any, List, Optional
from google.cloud import firestore
from app.core.config import db

class FirestoreMemory:
    def __init__(self, user_email: str):
        self.user_email = user_email.lower()
        # Path: wingman_users / {email} / history / {timestamp}
        self.history_ref = db.collection("wingman_users").document(self.user_email).collection("history")

    def add_user_message(self, content: str):
        """Saves the user's query to Firestore."""
        self.history_ref.add({
            "role": "user",
            "content": content,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

    def add_assistant_message(self, content: str, agent_name: str = "Director", trace: list = None):
        """Saves the AI's response and the technical trace to Firestore."""
        self.history_ref.add({
            "role": "assistant",
            "agent": agent_name,
            "content": content,
            "trace": trace or [], # This stores exactly what the agents did
            "timestamp": firestore.SERVER_TIMESTAMP
        })

    def get_focused_context(self, limit: int = 10, agent_filter: str = None) -> str:
        """Fetches recent history to give the AI context."""
        query = self.history_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
        docs = query.stream()
        
        history_lines = []
        # We reverse them to get chronological order for the LLM
        for doc in reversed(list(docs)):
            data = doc.to_dict()
            role = data.get("role", "user")
            content = data.get("content", "")
            history_lines.append(f"{role.upper()}: {content}")
        
        return "\n".join(history_lines)

    def get_last_trace_item(self) -> list:
        """Helper for follow-up queries (The index you just built is for this!)"""
        query = self.history_ref.where("role", "==", "assistant").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1)
        docs = list(query.stream())
        if docs:
            return docs[0].to_dict().get("trace", [])
        return []
    
    def get_all_history(self, limit: int = 50) -> list:
        """
        Retrieves a chronological list of chat messages for the UI.
        The 'random letters' you saw are Firestore Document IDs; 
        we ignore those and just pull the 'content' and 'role' inside.
        """
        try:
            # We order by timestamp so the conversation makes sense (oldest to newest)
            query = self.history_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
            docs = query.stream()

            history = []
            for doc in docs:
                data = doc.to_dict()
                
                # We extract only what the UI needs to stay clean
                history.append({
                    "role": data.get("role"),      # 'user' or 'assistant'
                    "content": data.get("content"), # The actual text
                    "agent": data.get("agent"),     # Which agent responded (if assistant)
                    "timestamp": data.get("timestamp").isoformat() if data.get("timestamp") else None
                })
            
            return history
        except Exception as e:
            logging.error(f"Error retrieving history for {self.user_email}: {e}")
            return []