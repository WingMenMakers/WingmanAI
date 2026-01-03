import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from google.cloud import firestore

class FirestoreMemory:
    def __init__(self, user_email: str):
        # Path to your service account key
        self.db = firestore.Client.from_service_account_json("config/service_account.json")
        self.user_email = user_email.lower()
        # Document reference for the user
        self.user_doc = self.db.collection("wingman_users").document(self.user_email)

    def add_user_message(self, content: str):
        """Adds a user message to the 'history' sub-collection."""
        self.user_doc.collection("history").add({
            "timestamp": firestore.SERVER_TIMESTAMP,
            "role": "user",
            "agent_name": "User",
            "content": content,
            "trace": []
        })

    def add_assistant_message(self, content: str, agent_name: str, trace: List[Dict]):
        """Adds the Director's response and execution trace to Firestore."""
        self.user_doc.collection("history").add({
            "timestamp": firestore.SERVER_TIMESTAMP,
            "role": "assistant",
            "agent_name": agent_name,
            "content": content,
            "trace": trace,
            "metadata": {}
        })

    def get_focused_context(self, agent_filter: str = None, limit: int = 5) -> str:
        """Fetches the last N turns and formats them for the LLM."""
        history_ref = self.user_doc.collection("history")
        # Order by time descending to get the most recent messages
        query = history_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
        
        relevant_turns = []
        # Firestore query results are returned as a stream
        for doc in query.stream():
            msg = doc.to_dict()
            # We use the same formatting logic you wrote in Chat_Memory.py
            relevant_turns.append(self._format_turn_for_llm(msg, agent_filter))
        
        # We reverse them because we queried the newest first, 
        # but LLMs need chronological order.
        return "\n\n".join(reversed(relevant_turns))

    def get_last_trace_item(self) -> Optional[Any]:
        """Retrieves the result of the very last successful agent action."""
        history_ref = self.user_doc.collection("history")
        # Get the most recent assistant message that has a trace
        query = history_ref.where("role", "==", "assistant").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1)
        
        for doc in query.stream():
            msg = doc.to_dict()
            if msg.get("trace"):
                return msg["trace"][-1].get("result")
        return None

    def _format_turn_for_llm(self, message: Dict, highlight_agent: str = None) -> str:
        # (Same logic from your Chat_Memory.py - parses JSON into a text string)
        role = message["role"].upper()
        content = message["content"]
        if role == "USER": return f"USER: {content}"
        
        trace_summary = ""
        if message.get("trace"):
            trace_items = [f"[{t.get('agent')}]: {str(t.get('result'))[:100]}" for t in message["trace"]]
            trace_summary = " | ".join(trace_items)
        
        return f"ASSISTANT (Trace): {trace_summary}\nResponse: {content}" if trace_summary else f"ASSISTANT: {content}"