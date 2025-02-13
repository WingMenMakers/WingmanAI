from Tools.MailTool import MailTool
from Agents.CommunicationAgent import CommunicationManager

# Create instances
mail_tool = MailTool()
comms_manager = CommunicationManager(mail_tool)

# User query (you can replace this with dynamic input)
user_query = "Can you send an email to Anuj asking for the update on the 'WingMan Project'?"

# Process request
response = comms_manager.handle_request(user_query)
print(response)

