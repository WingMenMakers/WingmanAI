import os
import json
import logging
from auth.token_manager import load_google_credentials
from auth.token_manager import load_linkedin_tokens
from google.oauth2.credentials import Credentials
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from typing import Dict, Any, List, Optional

# ---- Agent Imports ----
from agents.EmailAgent import EmailAgent
from agents.CalendarAgent import CalendarAgent
from agents.DocAgent import DocAgent
# from agents.ResearchAgent import ResearchAgent
from agents.WeatherAgent import WeatherAgent
from agents.WebsearchAgent import WebsearchAgent
from agents.LinkedinAgent import LinkedinAgent
## from agents.SpotifyAgent import SpotifyAgent
## from agents.YouTubeAgent import YouTubeAgent

# ---- Load environment ----
load_dotenv()

class Director:
    # Map agents to the required Google API scope from config/scopes.json
    AGENT_SCOPE_MAP = {
        "Email": ["https://mail.google.com/"],
        "Calendar": ["https://www.googleapis.com/auth/calendar"],
        "Doc": ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"],
        "Linkedin": ["w_member_social", "profile", "email"], # Use the actual LinkedIn scope name
        # Add non-Google agents here too, e.g., "linkedin": "r_liteprofile"
    }

    def __init__(self, user_email, chat_memory_instance=None):
        self.user_email = user_email
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.credentials: Credentials = None
        self.agents = {}
        self.conversation_history = []
        self.last_used_agent = None
        self.google_credentials = None
        self.linkedin_tokens = None
        self.user_scopes = set()
        self.chat_memory = chat_memory_instance # Store the reference to the memory system

        # 🎯 NEW: Task State Management
        # Stores the interrupted plan when a MISSING_DATA error occurs.
        self.pending_task_plan: Optional[List[Dict[str, str]]] = None 
        self.interrupted_step: Optional[int] = None
        self.raw_results_before_interruption: Dict[int, Any] = {}

        try:
            # Try loading Google credentials (refreshes if needed)
            self.google_credentials = load_google_credentials(user_email)
            self.user_scopes = set(self.google_credentials.scopes)
        except ValueError:
            self.user_scopes = set()
            logging.info(f"Google services not available for {user_email}.")
            
        try:
            # Try loading LinkedIn tokens (returns dict if available)
            self.linkedin_tokens = load_linkedin_tokens(user_email)
        except ValueError:
            logging.info(f"LinkedIn service not available for {user_email}.")

        # 2. Dynamically initialize agents based on granted scopes/available tokens
        for agent_name, required_scope_list in self.AGENT_SCOPE_MAP.items():
            agent_key = agent_name.lower()
            agent_class_name = f"{agent_name}Agent"
            AgentClass = globals().get(agent_class_name)

            if AgentClass:
                initialized = False
                # A. Google Agents check scope and credentials
                if agent_key in ["email", "calendar", "doc"]:
                    if self.google_credentials and all(scope in self.user_scopes for scope in required_scope_list):
                        self.agents[agent_key] = AgentClass(self.google_credentials)
                        logging.info(f"✅ Initialized {agent_name}Agent (Google).")
                        initialized = True
                
                # B. LinkedIn Agent check token dict availability
                elif agent_key == "linkedin":
                    # FIX: Renamed variable to avoid conflict with agent_name in previous scope
                    linkedin_key = "linkedin" # Use "linkedin" for lookup in self.agents
                    if self.linkedin_tokens:
                        self.agents[linkedin_key] = AgentClass(self.linkedin_tokens) 
                        logging.info(f"✅ Initialized LinkedInAgent.")
                        initialized = True
                
                if not initialized:
                    # If AgentClass was found but not initialized (i.e., missing tokens/scopes)
                    logging.info(f"❌ Skipping {agent_name}Agent: Scope/Token not granted.")
            else:
                logging.warning(f"Agent class {agent_class_name} not found.")

        # --- 3. Initialize Public/Unscoped Agents (Unconditional)
        try:
            self.agents["weather"] = WeatherAgent(credentials=None)
            logging.info("✅ Initialized WeatherAgent (Public).")
        except ImportError:
            logging.warning("WeatherAgent module not found.")

        try:
            self.agents["websearch"] = WebsearchAgent(credentials=None)
            logging.info("✅ Initialized WebsearchAgent (Public).")
        except ImportError:
            logging.warning("WebsearchAgent module not found.")

        # 4. Generate the dynamic system prompt
        self.system_prompt = self._generate_dynamic_system_prompt()

    def _generate_dynamic_system_prompt(self):
        """Generates the system prompt using only the agents available to the user."""
        
        # Start with the static instructions
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
            # Expected format: "Agent Error: MISSING_DATA_EMAIL_CONTACT; Sarah"
            name = raw_error.split("; ")[1].strip()
            question_prompt = f"The Email Agent needs the email address for the recipient named '{name}' to proceed with the original request: '{original_query}'. Please generate a simple, conversational question asking the user for the missing email address."
        
        elif "MULTIPLE_CONTACTS" in raw_error:
            # Expected format: "Agent Error: MULTIPLE_CONTACTS; Name: Sarah; Suggestions: - Sarah <s@g.com>..."
            parts = raw_error.split("; ")
            name_part = parts[1] # Name: Sarah
            suggestions_part = parts[2] # Suggestions: - Sarah <s@g.com>...
            question_prompt = f"The Agent found multiple contacts for {name_part}. The suggestions are: {suggestions_part}. Please ask the user to clarify which email address to use for the original request: '{original_query}'."
            
        elif "MISSING_DATA_CALENDAR_TIME" in raw_error or "TEMPORAL_RESOLUTION_FAILURE" in raw_error:
            # Calendar Agent missing time or can't resolve dependency
            question_prompt = f"The Calendar Agent couldn't determine the time for your event based on your original request: '{original_query}'. Could you please provide the exact start time and day?"

        elif "AMBIGUOUS_EVENT_MATCH" in raw_error or "EVENT_NOT_FOUND" in raw_error:
            # Calendar/Doc Agent ambiguity/not found error
            event_details = raw_error.split("Events:")[-1] if "Events:" in raw_error else ""
            question_prompt = f"I found an issue finding the exact item for your request: '{original_query}'. Could you specify which event/file you meant from these options (or provide the full name)? Details: {event_details}"

        else:
            # Catch-all generic missing data/incomplete status
            question_prompt = f"An agent requires more information to proceed with '{original_query}'. Raw detail: {raw_error}. Please ask the user what detail is missing/needed."

        # Call the self-agent LLM to formulate the conversational question
        try:
            messages = [
                {"role": "system", "content": "You are a courteous assistant. Based on the prompt, generate only the direct question/message needed to get the required information from the user. Do not add any introductory or concluding remarks."},
                {"role": "user", "content": question_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1
            ).choices[0].message.content.strip()

            return response # Return the final conversational string
            
        except Exception as e:
            logging.error(f"Error generating interruption question: {e}")
            return f"I need additional information, but I ran into a system error. Could you please rephrase your request? (Error: {raw_error})"
    
    # -------------------- Utility Functions --------------------

    def add_to_history(self, role, content):
        """Save conversation turns."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def _clean_json_response(self, text):
        """Cleans JSON returned by the model."""
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("```json").strip("```").strip()
        return text

    # -------------------- Query Analysis (Planner) --------------------
    
    def analyze_query(self, user_query) -> List[Dict[str, str]]:
        """
        Overrides the standard planner logic to incorporate RESUMPTION logic.
        """
        # 🎯 NEW: RESUMPTION LOGIC
        if self.pending_task_plan is not None:
            logging.info("Director is resuming a pending task.")

            # Combine the original query (the interrupted plan) with the new user input
            original_plan_steps = json.dumps(self.pending_task_plan)
            
            resumption_prompt = f"""
            The previous task was interrupted at step {self.interrupted_step} because it was missing information.
            The **original, incomplete plan** was: {original_plan_steps}
            The **raw results** gathered so far were: {json.dumps(self.raw_results_before_interruption)}
            The **user's last input (the answer)** is: "{user_query}"

            Your task is to generate a **NEW, complete sequential plan (Plan B)** in the required JSON list format. 

            RULES for Plan B:
            1. Plan B must incorporate the user's answer ("{user_query}") into the original task.
            2. You must repeat steps 1 through {self.interrupted_step - 1} using the results stored in raw_results_before_interruption to provide context, but ensure the failed step ({self.interrupted_step}) is now corrected using the user's answer.
            3. Use the user's answer to substitute the missing data.
            4. The final step must still be "agent": "self".

            Example Correction: If the user said 'sarah@example.com', Plan B's corrected step 2 (the previously failed step) should use 'sarah@example.com' instead of the placeholder.
            """

            try:
                # Call LLM with the context and the answer to generate the new plan
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": resumption_prompt}, 
                        {"role": "user", "content": "Generate the new Plan B now."}
                    ],
                    temperature=0.1
                ).choices[0].message.content.strip()

                cleaned = self._clean_json_response(response)
                plan = json.loads(cleaned)
                
                # Clear the state if planning is successful
                self.pending_task_plan = None 
                self.interrupted_step = None
                self.raw_results_before_interruption = {}

                if not isinstance(plan, list):
                    raise TypeError("Resumption Planner returned non-list or invalid structure.")
                return plan

            except Exception as e:
                logging.error(f"❌ Error generating resumption plan (Plan B): {e}")
                # Fallback to general self-query if planning fails
                return [{"agent": "self", "query": f"I received your answer, but I had trouble resuming the task. Can we start over? Original query: {user_query}"}]
        
        # Original planning logic for new queries
        else:
            return self._original_analyze_query(user_query)
        
    # Hiding the original analyze_query logic under a new private function
    def _original_analyze_query(self, user_query) -> List[Dict[str, str]]:
        # 🎯 NEW: Inject the last raw result into the planner prompt for context
        last_raw_output = None
        if self.chat_memory:
            # Assuming chat_memory.get_last_raw_result() is the correct function call
            last_raw_output = self.chat_memory.get_last_raw_result()

        context_injection = ""
        if last_raw_output:
            try:
                context_injection = f"\n\nCONTEXT INJECTION (Last Action Result): {json.dumps(last_raw_output)}"
            except Exception:
                context_injection = f"\n\nCONTEXT INJECTION (Last Action Result): {str(last_raw_output)}"

        prompt = self._generate_dynamic_system_prompt()

        # Inject context into the user message/prompt for the LLM
        final_user_prompt = f"{user_query}{context_injection}"

        try:
            response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": final_user_prompt}],
            temperature=0.1
            ).choices[0].message.content.strip()
            # ... (rest of the original planning logic)
            cleaned = self._clean_json_response(response)
            plan = json.loads(cleaned)
            if not isinstance(plan, list):
                if isinstance(plan, dict) and 'agent' in plan:
                    return [plan]
                raise TypeError("Planner returned non-list or invalid structure.")
            return plan
        except Exception as e:
            logging.error(f"❌ Error generating plan: {e}")
            return [{"agent": "self", "query": user_query}]

    # -------------------- Agent Handling (Dispatch/Executor) --------------------

    def call_agent(self, agent_name, query, context=None) -> Any:
        """Routes the query to the correct agent and returns the RAW execution result."""
        agent = self.agents.get(agent_name)
        
        if not agent:
            # If agent is missing, return a string error, which the orchestrator handles
            return f"Agent Error: Agent '{agent_name}' not enabled or found."

        try:
            # NOTE: All Field Agent handle_query methods must accept (query, context=None)
            # and return the raw data/string or dictionary result directly.
            response = agent.handle_query(query, context=context)
            self.last_used_agent = agent_name
            return response
            
        except Exception as e:
            logging.error(f"Error in {agent_name} agent: {e}")
            return f"Agent Error in {agent_name}: {str(e)}"
        
    def structure_response(self, response_text):
        """Cleans and structures agent or model responses."""
        if not response_text:
            return "I couldn't find any useful information."
        return response_text.strip().replace("\n\n", "\n")

    # -------------------- Director Main Handler (Orchestration Logic) --------------------

    def handle_query(self, user_query) -> Dict[str, Any]:
        """
        Primary interface for main.py. Executes the multi-step plan, handling interruptions.
        """
        # If we are resuming a task, we need to pass the user's answer for planning, 
        # but we skip adding the one-word answer to history for a cleaner log.
        if self.pending_task_plan is None:
             self.add_to_history("user", user_query)

        # 1. Generate the Plan (Will be Plan A or the Resumption Plan B)
        execution_plan = self.analyze_query(user_query)
        
        if not execution_plan:
            return "I couldn't generate a valid execution plan for your request."

        # Initialize state management for the current execution run
        execution_results = self.raw_results_before_interruption.copy()
        final_message = None
        final_raw_context = None # Track the final raw data object

        # Capture the index of the last step and its agent key (needed for the final fallback block)
        last_step_index = 0
        last_agent_key = None
        
        # 2. Execute the Plan Steps
        for step_index, step in enumerate(execution_plan):
            step_number = step_index + 1
            agent_key = step.get("agent")
            query = step.get("query", "")

            last_step_index = step_index
            last_agent_key = agent_key # Update tracking variables

            if not agent_key:
                final_message = f"Plan error at step {step_number}: Missing agent key."
                break
                
            # Substitute results from previous steps (State Management)
            if "{{" in query and "}}" in query:
                for n, result in execution_results.items():
                    placeholder = f"{{$STEP_{n}_RESULT}}"
                    # We assume raw result is a string for substitution
                    query = query.replace(placeholder, str(result))

            logging.info(f"Executing Step {step_number}: Agent={agent_key}, Query='{query[:50]}...'")

            # --- Execute Agent Call ---
            if agent_key == "self":
                # Handle self-query (which acts as the formatter/planner confirmation)
                raw_result = self._handle_self_query(query)
            else:
                raw_result = self.call_agent(agent_key, query)
                
            # --- New: Parse Agent's Structured Response ---
            agent_response = self._parse_agent_response(raw_result)
            status = agent_response["status"]
            context_dict = agent_response["context"] # Now guaranteed to be a dict
            
            # Capture raw result for substitution/history 
            execution_results[step_number] = raw_result 
            self.add_to_history(f"step_{step_number}_result", json.dumps(raw_result))

            # -------------------- Status-Driven Flow Control --------------------

            if status == "INCOMPLETE":
                # 1. INTERRUPT
                logging.warning(f"Execution interrupted at step {step_number}. Status: {status}")
                
                # Store state for resumption
                self.pending_task_plan = execution_plan 
                self.interrupted_step = step_number
                self.raw_results_before_interruption = execution_results 
                
                # Use context_dict to get the reason/question for the user
                # We assume agent handles basic message generation for interruption
                error_detail = context_dict.get('reason', 'Missing data or ambiguity.')
                question_message = self._generate_interruption_question(error_detail, user_query) 
                
                final_message = self.structure_response(question_message)
                break 

            elif status == "ERROR" or status == "FATAL_ERROR":
                # 2. FATAL ERROR
                error_detail = context_dict.get('reason', 'Unknown system failure.')
                final_message = self.structure_response(f"❌ Execution halted at step {step_number}. Reason: {error_detail}")
                break

            # 3. COMPLETE: Check for final step completion (success)
            if step_number == len(execution_plan):
                
                # A. Distributed Formatting Priority (Step A3)
                if agent_key == "self":
                    # Self agent always returns the conversational string directly
                    final_message = self.structure_response(context_dict.get('raw_data', raw_result))
                    final_raw_context = None
                else:
                    agent_message = context_dict.get('message')
                    final_raw_context = context_dict.get('raw_data') # The dict/list we want to save
                    
                    if agent_message:
                        # Agent provided the final formatted message (OPTIMIZED PATH)
                        logging.info("Final message provided by Agent.")
                        final_message = self.structure_response(agent_message)
                    elif final_raw_context:
                        # Agent provided raw data but no message (FALLBACK PATH)
                        logging.info("Final step requires Director LLM formatting (FALLBACK).")
                        final_message = self.structure_response(
                            self._format_raw_output_via_llm(final_raw_context, user_query)
                        )
                    else:
                        # Should not happen if agent returned COMPLETE status
                        final_message = self.structure_response("Task completed, but no information was returned.")

                break # Exit the loop after processing the final step
            
        # 3. Final Return (Contract C)
        if not final_message:
            final_message = self.structure_response(f"Internal Logic Error: Task finished unexpectedly.")
            
        self.add_to_history("assistant", final_message)
            
        return {
            "message": final_message,
            "raw_data": final_raw_context, # Now correctly passes the final raw context
            "agent_key": last_agent_key
        }

    def _handle_self_query(self, user_query):
        """Handles the fallback general conversation query."""
        messages = [{"role": "user", "content": user_query}]
        
        reply = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        ).choices[0].message.content.strip()
        return reply

    # -------------------- NEW: Status Parsing and Formatting --------------------

    def _format_raw_output_via_llm(self, context: Any, user_query: str) -> str:
        """
        Called when a complex, non-string context (list/dict) needs conversational formatting.
        This replaces the formatting logic we had in the previous iteration's final step.
        """
        try:
            # Use json.dumps to safely serialize the complex data structure for the LLM
            raw_data_string = json.dumps(context)
        except TypeError:
            # Fallback if the data cannot be serialized (e.g., contains an object)
            raw_data_string = str(context)

        # Use a specific, strict prompt to ensure concise output
        system_prompt = """You are WingMan's Final Formatter. Your task is to convert raw system output (JSON list/dict) into a brief, conversational message for the user.
    
        RULES for output:
        1. If the input contains email data, list ONLY the Sender and Subject for the top 5 items. Be extremely concise.
        2. If the input contains structured data (e.g., weather or search results), structure the summary clearly.
        3. If the input is a short status (e.g., 'Doc created with ID: XYZ'), confirm the action simply.
        4. Do not include introductory phrases like 'Based on the data...' just deliver the message.
        """
    
        prompt = f"Original Query: {user_query}. Raw Data to Format: {raw_data_string}"

        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1 # Low temperature for deterministic formatting
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"System Error: Failed to generate final conversational output. Raw data context: {raw_data_string}"
    
    def _parse_agent_response(self, raw_result: Any) -> Dict[str, Any]:
        """
        Converts the Agent's raw output (string or dict) into the unified, simplified status structure:
        {"status": "COMPLETE"/"INCOMPLETE"/"ERROR", "action": str, "context": Dict} 
        
        The context dict must contain: 'message', 'raw_data', and/or 'reason'/'question'.
        """
        # Prefer dictionary output from the Agent (New Contract)
        if isinstance(raw_result, dict) and 'status' in raw_result and 'action' in raw_result:
            # Enforce simplified statuses and ensure context is a dict for consistency
            status = raw_result['status'].upper().split(':')[0]
            
            if status not in ["COMPLETE", "INCOMPLETE", "ERROR", "FATAL_ERROR"]:
                 status = "ERROR" # Default to Error if status code is non-standard
                 
            # Ensure context is always a dictionary for structured access
            context_data = raw_result.get('context', {})
            if not isinstance(context_data, dict):
                 context_data = {"raw_data": context_data}
                 
            return {
                "status": status,
                "action": raw_result['action'],
                "context": context_data
            }
        
        # --- Fallback to parse old string formats (Crucial for existing agents) ---
        if isinstance(raw_result, str):
            if raw_result.startswith("Agent Error:"):
                # Handle Fatal Error strings (old format)
                return {
                    "status": "ERROR", 
                    "action": "N/A", 
                    "context": {"reason": raw_result}
                }
            
        # If it's a raw string or list/dict from a successful step that didn't use the new dict format
        # We assume successful raw data execution (OLD COMPLETE: RAW_DATA)
        # This will be processed by the final step logic for formatting.
        return {
            "status": "COMPLETE",
            "action": "N/A", # Action is unknown in this case
            "context": {"raw_data": raw_result, "message": None} 
        }

    def _find_last_raw_result(self, target_agent_key: str) -> Optional[Any]:
        """
        Searches conversation history for the most recent successful raw result 
        from a specific agent to use as follow-up context.
        """
        # We prioritize searching the last 5 entries of the full history
        # for the relevant result tag (e.g., step_N_result).
        
        # Iterate backwards through history
        for entry in reversed(self.conversation_history):
            if entry["role"].startswith("step_"):
                # Check if the preceding message/plan involved the target agent
                # This is complex, so for simplicity, we check if the entry content
                # contains a structured status we recognize (RAW_DATA, RAW_STATUS).
                
                content = entry["content"]
                
                # Since the raw result (List/Dict) is stored as a stringified object in history,
                # we check for common success markers to identify relevant data.
                if content.startswith("RAW_DATA:") or content.startswith("RAW_STATUS:") or content.startswith("[{"):
                    # We need a robust way to match the agent to the result.
                    # A simpler initial approach is to check the last executed step index.
                    # Since the actual agent key of the execution result is not stored 
                    # in the current history structure, let's rely on the Planner LLM 
                    # to do the hard work and just retrieve the *entire* raw output 
                    # of the previous successful step (before it was formatted).
                    
                    # --- SIMPLIFIED CONTEXT RETRIEVAL (Best Practice for Orchestration) ---
                    # Return the result of the *last executed step* before the current one.
                    # We look at the largest index in execution_results.
                    
                    if self.execution_results:
                        last_step_num = max(self.execution_results.keys())
                        last_raw_result = self.execution_results.get(last_step_num)
                        
                        # Ensure the data is still available before returning
                        if last_raw_result and isinstance(last_raw_result, (list, dict)):
                            return last_raw_result

        return None