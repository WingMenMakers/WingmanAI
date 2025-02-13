from langchain.memory import ConversationBufferMemory
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize Firebase
firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_credentials_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

class FirebaseMemory(ConversationBufferMemory):
    def __init__(self, user_id, agent_name, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.agent_name = agent_name

    def save_context(self, inputs, outputs):
        """Save conversation history to Firestore."""
        super().save_context(inputs, outputs)  # Store in-memory first
        doc_ref = db.collection("conversations").document(self.user_id).collection(self.agent_name).document()
        doc_ref.set({"input": inputs["input"], "output": outputs["output"]})

    def load_memory_variables(self, inputs):
        """Load past conversation history from Firestore."""
        messages = db.collection("conversations").document(self.user_id).collection(self.agent_name).stream()
        history = "\n".join(f"{msg.to_dict().get('input')} -> {msg.to_dict().get('output')}" for msg in messages)
        return {"history": history} if history else {"history": ""}
