from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from memory.firebase_memory import FirebaseMemory
from agents.communication_agent import CommunicationAgent

class DirectorAgent:
    def __init__(self, user_id):
        self.memory = FirebaseMemory(user_id, "director_agent")
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.communication_agent = CommunicationAgent(user_id)
        
        self.available_agents = {
            "communication": self.communication_agent
        }

    def determine_agent(self, user_input):
        """
        Uses LLM to decide which agent should handle the request.
        """
        prompt = f"""
        You are a system that routes user requests to the correct agent.
        
        ### Instructions:
        - The user request is given below.
        - You must return ONLY the agent name that should handle it.
        - Available agents: {', '.join(self.available_agents.keys())}.
        - Respond with just the agent name (e.g., 'communication'), nothing else.
    
        ### User Request:
        "{user_input}"
        """

    response = self.llm.invoke(prompt)
    agent_name = response.content.strip().lower()

    return self.available_agents.get(agent_name, None)


    def route_request(self, user_input):
        """
        Routes user input to the correct agent, then rephrases the response.
        """
        selected_agent = self.determine_agent(user_input)
        if selected_agent:
            response = selected_agent.handle_request(user_input)
        else:
            response = "I'm not sure how to handle that request."

        # Rephrase the response to ensure it directly resolves the user's query
        final_response = self.llm.predict(
            f"Rephrase the following response to be clearer and more helpful:\nResponse: {response}"
        )

        self.memory.save_context({"input": user_input}, {"output": final_response})
        return final_response
