# memory/chat_memory.py
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class ChatMemory:
    def __init__(self, user_email=None, base_dir="memory"):
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        file_name = f"{user_email}_chat_history.json" if user_email else "chat_history.json"
        self.file_path = os.path.join(base_dir, file_name)
        self.history = self._load_history()
        self.current_conversation_id = None

    def _load_history(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading chat history: {e}")
        return {"conversations": []}

    def _save_history(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving chat history: {e}")

    def start_new_conversation(self):
        new_id = len(self.history["conversations"]) + 1
        conversation = {
            "id": new_id,
            "timestamp": datetime.now().isoformat(),
            "messages": []
        }
        self.history["conversations"].append(conversation)
        self.current_conversation_id = new_id
        self._save_history()
        return new_id

    def add_message(self, role, content, metadata=None):
        if not self.current_conversation_id:
            self.start_new_conversation()
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            message["metadata"] = metadata
        self.history["conversations"][self.current_conversation_id - 1]["messages"].append(message)
        self._save_history()

    def get_recent_messages(self, limit=5):
        if not self.current_conversation_id:
            return []
        return self.history["conversations"][self.current_conversation_id - 1]["messages"][-limit:]

    def get_last_raw_result(self) -> Optional[Any]:
        """
        Retrieves the RAW output from the last assistant message's metadata.
        Used by the Director for Contextual Injection.
        """
        if not self.current_conversation_id:
            return None
        
        current_conv = self.history["conversations"][self.current_conversation_id - 1]["messages"]
        
        # Iterate backwards to find the last response from the assistant
        for message in reversed(current_conv):
            if message["role"] == "assistant":
                # Look for the 'raw_result' key in the metadata
                raw_data = message.get("metadata", {}).get("raw_result")
                
                # Check if raw_data exists and is a complex structure (list or dict)
                if raw_data and isinstance(raw_data, (list, dict)):
                    # We found the raw output from the last executed step
                    return raw_data
                
                # Fallback: if we find an assistant message but no raw_data, stop looking
                # to prevent retrieving irrelevant data from older turns.
                return None 
        
        return None