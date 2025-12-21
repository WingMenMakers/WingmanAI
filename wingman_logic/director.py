import json
import logging
from typing import Dict, Any, List, Optional

# ---- FastAPI Core Config Import ----
from app.core.config import settings

# ---- Standard Library Imports ----
from google.oauth2.credentials import Credentials
from openai import OpenAI

# ---- Refactored WingMan Logic Imports ----
from wingman_logic.auth.token_manager import load_google_credentials, load_linkedin_tokens
from wingman_logic.agents.EmailAgent import EmailAgent
from wingman_logic.agents.CalendarAgent import CalendarAgent
from wingman_logic.agents.DocAgent import DocAgent
from wingman_logic.agents.WeatherAgent import WeatherAgent
from wingman_logic.agents.WebsearchAgent import WebsearchAgent
from wingman_logic.agents.LinkedinAgent import LinkedinAgent

# --- Revised Flow ---
# 1. API receives request -> auth.py validates token
# 2. sessions.py injects Director (using cache)
# 3. main.py calls Director.handle_query() inside a threadpool

class Director:
    AGENT_SCOPE_MAP = {
        "Email": ["https://mail.google.com/"],
        "Calendar": ["https://www.googleapis.com/auth/calendar"],
        "Doc": ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"],
        "Linkedin": ["w_member_social", "profile", "email"], 
    }

    def __init__(self, user_email, chat_memory_instance):
        self.user_email = user_email
        # REFACTOR: Use settings for API Key
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Injected from sessions.py (FirestoreMemory instance)
        self.chat_memory = chat_memory_instance
        
        self.agents = {}
        self.google_credentials = None
        self.linkedin_tokens = None
        self.user_scopes = set()

        # 🎯 Task State Management
        self.pending_task_plan: Optional[List[Dict[str, str]]] = None 
        self.interrupted_step: Optional[int] = None
        self.raw_results_before_interruption: Dict[int, Any] = {}

        self._initialize_auth()
        self._initialize_agents()
        self.system_prompt_base = self._generate_dynamic_system_prompt()

    def _initialize_auth(self):
        try:
            self.google_credentials = load_google_credentials(self.user_email)
            self.user_scopes = set(self.google_credentials.scopes)
        except ValueError:
            logging.info(f"Google services not available for {self.user_email}.")
            
        try:
            self.linkedin_tokens = load_linkedin_tokens(self.user_email)
        except ValueError:
            logging.info(f"LinkedIn service not available for {self.user_email}.")

    def _initialize_agents(self):
        for agent_name, required_scope_list in self.AGENT_SCOPE_MAP.items():
            agent_key = agent_name.lower()
            AgentClass = globals().get(f"{agent_name}Agent")

            if AgentClass:
                initialized = False
                if agent_key in ["email", "calendar", "doc"]:
                    if self.google_credentials and all(scope in self.user_scopes for scope in required_scope_list):
                        self.agents[agent_key] = AgentClass(self.google_credentials)
                        initialized = True
                elif agent_key == "linkedin" and self.linkedin_tokens:
                    self.agents[agent_key] = AgentClass(self.linkedin_tokens) 
                    initialized = True
                
                if initialized:
                    logging.info(f"✅ Initialized {agent_name}Agent.")
            else:
                logging.warning(f"Agent class {agent_name}Agent not found.")

        # Initialize Public Agents (Tavily key injected via settings)
        try:
            self.agents["weather"] = WeatherAgent(credentials=None)
            if settings.TAVILY_API_KEY:
                self.agents["websearch"] = WebsearchAgent(api_key=settings.TAVILY_API_KEY)
        except Exception as e:
            logging.error(f"Failed to load public agents: {e}")

    # -------------------- 1. Context Analysis (The "Brain" Filter) --------------------

    def _get_relevant_history(self, user_query: str) -> str:
        available_agents = list(self.agents.keys())
        prompt = f"""User Query: "{user_query}"\nAvailable Agents: {available_agents}
        Does this require context from an agent? Return ONLY the agent name or "NONE"."""
        
        try:
            res = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            ).choices[0].message.content.strip().lower()
        except Exception:
            res = "none"

        agent_filter = res if res in available_agents else None
        return self.chat_memory.get_focused_context(agent_filter=agent_filter)
    
    def _get_last_action_context(self) -> str:
        """
        Retrieves the raw result of the very last action and formats it 
        specifically for ID extraction (avoiding memory truncation).
        """
        raw_data = self.chat_memory.get_last_trace_item()
        if not raw_data or not isinstance(raw_data, list):
            return ""

        formatted_items = []
        for item in raw_data:
            item_id = item.get("id") or item.get("event_id")
            item_name = item.get("subject") or item.get("event_name") or item.get("name") or "Unknown"
            if item_id:
                formatted_items.append(f"• ID: {item_id} | Name: {item_name}")
        
        return "\nCONTEXT INJECTION (Recent Items):\n" + "\n".join(formatted_items) if formatted_items else ""

    # -------------------- 2. Planner --------------------
    
    def analyze_query(self, user_query: str) -> List[Dict[str, str]]:
        if self.pending_task_plan is not None:
            return self._generate_resumption_plan(user_query)
        
        history_context = self._get_relevant_history(user_query)
        active_context = self._get_last_action_context()
        
        full_system_prompt = (
            f"{self.system_prompt_base}\n\n"
            f"=== RELEVANT MEMORY ===\n{history_context}\n\n"
            f"{active_context}\n"
            f"=== END MEMORY ==="
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": full_system_prompt}, 
                    {"role": "user", "content": user_query}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            ).choices[0].message.content.strip()
            
            plan = json.loads(self._clean_json_response(response))
            # Support both single dict and list of dicts
            return plan if isinstance(plan, list) else [plan]
        except Exception as e:
            logging.error(f"❌ Planning Error: {e}")
            return [{"agent": "self", "query": user_query}]

    def _generate_resumption_plan(self, user_answer: str) -> List[Dict[str, str]]:
        resumption_prompt = f"""Task interrupted at step {self.interrupted_step}. 
        User Answer: "{user_answer}". Original Plan: {json.dumps(self.pending_task_plan)}.
        Generate a new JSON Plan B list."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": resumption_prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            ).choices[0].message.content.strip()
            
            plan = json.loads(self._clean_json_response(response))
            self.pending_task_plan = None # Clear state
            return plan if isinstance(plan, list) else [plan]
        except Exception:
            return [{"agent": "self", "query": user_answer}]
        
    # -------------------- 3. Main Handler --------------------

    def handle_query(self, user_query: str) -> Dict[str, Any]:
        if self.pending_task_plan is None:
            self.chat_memory.add_user_message(user_query)

        execution_plan = self.analyze_query(user_query)
        execution_results = self.raw_results_before_interruption.copy()
        current_trace = [] 
        final_message = ""
        last_agent = "Director"
        
        for step_index, step in enumerate(execution_plan):
            step_number = step_index + 1
            agent_key = step.get("agent")
            query = step.get("query", "")
            
            # Variable Substitution
            if "{{" in query:
                for n, res in execution_results.items():
                    query = query.replace(f"{{$STEP_{n}_RESULT}}", str(res))

            # --- EXECUTE ---
            if agent_key == "self":
                raw_result = self._handle_self_query(query)
                parsed_response = {"status": "COMPLETE", "action": "chat", "context": {"raw_data": raw_result, "message": raw_result}}
            else:
                raw_result = self.call_agent(agent_key, query)
                parsed_response = self._parse_agent_response(raw_result)

            status = parsed_response["status"]
            context_data = parsed_response["context"]
            
            # Update Trace
            trace_entry = {
                "step": step_number, "agent": agent_key,
                "action": parsed_response.get("action", query),
                "result": context_data.get("raw_data"),
                "status": status
            }
            current_trace.append(trace_entry)
            execution_results[step_number] = context_data.get("raw_data")
            last_agent = agent_key

            # Flow Control
            if status == "INCOMPLETE":
                self.pending_task_plan = execution_plan
                self.interrupted_step = step_number
                self.raw_results_before_interruption = execution_results
                final_message = self._generate_interruption_question(context_data.get("reason", ""), user_query)
                break 
            elif status in ["ERROR", "FATAL_ERROR"]:
                final_message = f"❌ Error: {context_data.get('reason')}"
                break
            
            if step_number == len(execution_plan):
                final_message = context_data.get("message") or self._format_raw_output_via_llm(context_data.get("raw_data"), user_query)

        # 💾 Persistence
        self.chat_memory.add_assistant_message(content=final_message, agent_name=last_agent, trace=current_trace)

        return {"message": final_message, "agent_key": last_agent}

    # -------------------- Utilities --------------------

    def call_agent(self, agent_name, query) -> Any:
        agent = self.agents.get(agent_name)
        if not agent:
            return {"status": "ERROR", "action": "N/A", "context": {"reason": f"Agent {agent_name} not found"}}
        try:
            return agent.handle_query(query)
        except Exception as e:
            return {"status": "ERROR", "action": "N/A", "context": {"reason": str(e)}}
        
    def _parse_agent_response(self, raw_result: Any) -> Dict:
        """Enforces the dictionary contract."""
        if isinstance(raw_result, dict) and "status" in raw_result:
            return raw_result
        return {
            "status": "COMPLETE",
            "action": "unknown",
            "context": {"raw_data": raw_result}
        }
    
    def _clean_json_response(self, text):
        return text.strip().replace("```json", "").replace("```", "").strip()

    def _handle_self_query(self, query):
        messages = [{"role": "user", "content": query}]
        return self.client.chat.completions.create(
            model="gpt-4o-mini", messages=messages
        ).choices[0].message.content.strip()

    def _generate_dynamic_system_prompt(self):
        # (FULL PROMPT STRING FROM PREVIOUS MESSAGES GOES HERE - REMOVED FOR BREVITY BUT MUST BE INCLUDED)
        # Please paste the full prompt string you have from previous turns here.
        prompt = """You are WingMan's Director — an intelligent coordinator and assistant. You analyze user input and route it to the correct specialized agent.

🧠 ALWAYS return a valid JSON **single JSON list of objects** where each object MUST have the following structure:
{{
    "agent": "name_of_agent",
    "query": "user's query meant for that agent"
}}

RULES:
1. Only include `agent` and `query` keys. DO NOT include actions, parameters, or any other fields.
2. List the steps chronologically.
3. If a step's query depends on the raw result of a previous step, use the exact placeholder **{{$STEP_[N]_RESULT}}** where [N] is the 1-based index of the previous step.
4. If the request is simple (e.g., just 'check email'), the plan should contain only one step.
5. If no specialized agent is needed, use "agent": "self".
6. **CRITICAL CONTEXTUAL RETRIEVAL:** If the user's query is a follow-up ("Read that," "Reply to mail X," "Summarize the file"), you MUST generate a new action query that is a precise retrieval instruction. The new action query MUST include the unique ID (message_id, doc_id, etc.) extracted from the 'CONTEXT INJECTION'.

Example Follow-up Plan:
User: "Read me the mail from Canva."
Context Injection: [{"id": "19b1121d6d853e79", "subject": "..."}, ...]

Output Example for Follow-up:
[
    {"agent": "email", "query": "Retrieve full content for ID: 19b1121d6d853e79"}
]

---

User Query Template:
Example: "Find the price of gold and save it to a new file called Gold Report."
Output Example:
    [
        {{"agent": "websearch", "query": "current price of gold"}},
        {{"agent": "doc", "query": "create a new document named 'Gold Report' with the content: {{$STEP_1_RESULT}}"}},
        {{"agent": "self", "query": "confirm the document was created based on the previous steps."}}
    ]

---

🟡 Use these agents:

"""
        # Dictionary mapping agent names to descriptions (needs to be defined centrally or loaded)
        AGENT_DESCRIPTIONS = {
            "email": """
📧 **Email Agent** – for anything related to email:
{
    "agent": "email",
    "query": "user's email request like 'send an email to Alex' or 'check unread emails'"
}

Examples:
- "Send an email to Riya about the presentation"
- "Show me emails from Google"
- "Reply to John's message with a thank you"
""",
            "calendar": """📅 **Calendar Agent** – for scheduling, editing, or checking events:
{
    "agent": "calendar",
    "query": "calendar-related request like 'schedule a call at 3PM', 'delete my event tomorrow'"
}

Examples:
- "Add a meeting with Dev at 10AM"
- "Show my events for next week"
""",
            "doc": """📄 **Doc Agent** – for working with documents or notes:
{
    "agent": "doc",
    "query": "document or note related request like 'summarize this', 'search notes on finance'"
}

Examples:
- "Summarize the report I uploaded"
- "Find my notes on statistics"
""",
            "weather": """⛅ **Weather Agent** – for anything about the weather:
{
    "agent": "weather",
    "query": "weather-related request with location if mentioned"
}

Examples:
- "What's the weather like in Mumbai?"
- "Will it rain this weekend?"
""",
            "websearch": """🔍 **Web Search Agent** – for looking up anything online:
{
    "agent": "websearch",
    "query": "search query or knowledge-based question"
}

Examples:
- "What is generative AI?"
- "Latest news about cricket"
- "How does a black hole form?"
""",
            "research": """📚 **Research Agent** – for help with academic references, research material, or study topics:
{
    "agent": "research",
    "query": "request for academic help like 'give me 10 papers on machine learning' or 'list resources on quantum computing'"
}

Examples:
- "Give me 10 research papers on blockchain"
- "List references on fuzzy logic and its applications"
- "Find textbooks on data structures with summaries and links"
""",
            "linkedin": """💼 **LinkedIn Agent** – for interacting with LinkedIn:
{
    "agent": "linkedin",
    "query": "LinkedIn-related actions like 'send a connection request', 'search for jobs', or 'message a recruiter', or 'schedule a post'"
}

Examples:
- "Connect with the hiring manager at Google"
- "Send a thank you message to Sarah on LinkedIn"
- "Search for internships in data science"
""",
            "spotify": """🎵 **Spotify Agent** – for playing or managing music on Spotify:
{
    "agent": "spotify",
    "query": "Spotify music-related requests like 'play a song', 'add to playlist', or 'recommend music'"
}

Examples:
- "Play some Lo-fi beats"
- "Add this song to my workout playlist"
- "Recommend me some chill jazz"
""",
            "youtube": """📺 **YouTube Agent** – for searching and interacting with YouTube:
{
    "agent": "youtube",
    "query": "YouTube-related requests like 'search for a video', 'play something', or 'get video links'"
}

Examples:
- "Search YouTube for tutorials on ReactJS"
- "Play lo-fi music from YouTube"
- "Find the latest video by MKBHD"
""",    # Add descriptions for all potential agents here...
        }

        # Dynamically append available agents and their descriptions
        for agent_name in self.agents.keys():
            if agent_name in AGENT_DESCRIPTIONS:
                # This needs to be expanded to include the JSON format and examples
                # For brevity, we'll just add the header. You will need to fill out the full block.
                prompt += f"{AGENT_DESCRIPTIONS[agent_name]}\n" 

        # Always include the fallback self agent
        prompt += """💬 **Self (General Conversation)** – for normal questions, jokes, or discussion:
{
    "agent": "self",
    "query": "the user query as-is"
}

Examples:
- "What's your favorite movie?"
- "Tell me a joke"

"""
        return prompt
    
    # -------------------- Interruption & Resumption Logic --------------------

    def _generate_interruption_question(self, raw_error: str, original_query: str) -> str:
        """
        Generates the conversational question string to ask the user, based on the structured error.
        
        :param raw_error: The context from the INCOMPLETE status (e.g., "Agent Error: MISSING_DATA_EMAIL_CONTACT; Sarah").
        :param original_query: The user's original query.
        :return: The final, ready-to-display conversational question string.
        """
        
        # 1. Determine the intent of the missing data based on the structured string
        if "MISSING_DATA_EMAIL_CONTACT;" in raw_error:
            name = raw_error.split("; ")[1].strip()
            question_prompt = f"The Email Agent needs the email address for '{name}'. Original request: '{original_query}'."
        elif "MULTIPLE_CONTACTS" in raw_error:
            parts = raw_error.split("; ")
            name_part = parts[1]
            suggestions_part = parts[2]
            question_prompt = f"The Agent found multiple contacts for {name_part}: {suggestions_part}. Original request: '{original_query}'."
        elif "MISSING_DATA_CALENDAR_TIME" in raw_error:
            question_prompt = f"The Calendar Agent needs the start time. Original request: '{original_query}'."
        elif "AMBIGUOUS_EVENT_MATCH" in raw_error:
            event_details = raw_error.split("Events:")[-1]
            question_prompt = f"Ambiguous event match. Details: {event_details}. Original request: '{original_query}'."
        else:
            question_prompt = f"Missing info: {raw_error}. Request: '{original_query}'."

        try:
            messages = [
                {"role": "system", "content": "You are a courteous assistant. Generate a direct question for the missing info."},
                {"role": "user", "content": question_prompt}
            ]
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, temperature=0.1
            ).choices[0].message.content.strip()
            return response
        except Exception:
            return f"I need additional information. (Error: {raw_error})"
        
    # -------------------- NEW: Status Parsing and Formatting --------------------

    def _format_raw_output_via_llm(self, context: Any, user_query: str) -> str:
        try:
            raw_data_string = json.dumps(context)
        except TypeError:
            raw_data_string = str(context)

        system_prompt = """You are WingMan's Final Formatter. Convert raw JSON list/dict into a conversational message.
        1. If email data, list Sender and Subject for top 5.
        2. If structured data, structure clear summary.
        3. Be concise.
        """
        prompt = f"Original Query: {user_query}. Raw Data: {raw_data_string}"

        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                temperature=0.1
            )
            return completion.choices[0].message.content.strip()
        except Exception:
            return f"System Error formatting output. Raw data: {raw_data_string}"