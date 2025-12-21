# wingman_logic/memory/firestore_memory.py

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.core.config import settings

# --- IMPORTANT: This is a synchronous mock of an asynchronous I/O system ---
# In a real setup, this would use a Firestore async client (e.g., aiogoogle, async-gcp-firestore).
# For the purpose of Director (which is run in a thread pool), we define it 
# as synchronous but structure it for future async adoption.

class FirestoreMemory:
    def __init__(self, user_email: str):
        # Base directory comes from settings or default
        self.base_dir = "memory"
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        
        self.user_email = user_email
        # Files are uniquely named per user to prevent state leakage
        self.file_name = f"{user_email}_memory.json"
        self.file_path = os.path.join(self.base_dir, self.file_name)
        self.history = self._load_history()

    def _load_history(self) -> List[Dict]:
        """Loads the user's specific history stream."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Support for migrating old 'conversations' format if necessary
                    if isinstance(data, dict) and "conversations" in data:
                         return [m for conv in data["conversations"] for m in conv["messages"]]
                    return data
            except Exception as e:
                logging.error(f"Error loading chat history for {self.user_email}: {e}")
        return []

    def _save_history(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving chat history for {self.user_email}: {e}")

    def add_user_message(self, content: str):
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": "user",
            "agent_name": "User",
            "content": content,
            "trace": [] 
        }
        self.history.append(message)
        self._save_history()

    def add_assistant_message(self, content: str, agent_name: str = "Director", 
                                trace: List[Dict] = None, metadata: Dict = None):
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": "assistant",
            "agent_name": agent_name,
            "content": content,
            "trace": trace or [], 
            "metadata": metadata or {}
        }
        self.history.append(message)
        self._save_history()

    # --- READING MEMORY (New Optimized Context) ---

    def get_focused_context(self, agent_filter: str = None, limit: int = 5) -> str:
        """New optimized context retrieval logic integrated for multi-user."""
        relevant_turns = []
        count = 0
        for message in reversed(self.history):
            if count >= limit: break
            is_relevant = not agent_filter or message.get("agent_name") == agent_filter
            if not is_relevant and agent_filter:
                for step in message.get("trace", []):
                    if step.get("agent") == agent_filter:
                        is_relevant = True
                        break
            if is_relevant:
                relevant_turns.append(self._format_turn_for_llm(message, agent_filter))
                count += 1
        return "\n\n".join(reversed(relevant_turns))

    def _format_turn_for_llm(self, message: Dict, highlight_agent: str = None) -> str:
        role = message["role"].upper()
        content = message["content"]
        if role == "USER": return f"USER: {content}"
        
        trace_summary = ""
        if message.get("trace"):
            trace_items = []
            for item in message["trace"]:
                if highlight_agent and item.get("agent") != highlight_agent: continue 
                result_snippet = str(item.get("result", ""))[:200]
                action = item.get("action", "Unknown Action")
                trace_items.append(f"[{action}]: {result_snippet}")
            if trace_items: trace_summary = " | ".join(trace_items)
        
        return f"ASSISTANT (Trace): {trace_summary}\nResponse: {content}" if trace_summary else f"ASSISTANT: {content}"

    def get_last_trace_item(self) -> Optional[Any]:
        for message in reversed(self.history):
            if message["role"] == "assistant" and message.get("trace"):
                return message["trace"][-1].get("result")
        return None