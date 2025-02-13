import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)


# Chat Loop
while True:
    user_input = input("You: ")
    
    # Exit Chat Loop
    if user_input.lower() == "/bye":
        break

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "assistant", "content": "You are Wingman, a multi-agent assistant."},
            {"role": "user", "content": user_input},
        ],
    )

    response = completion.choices[0].message.content
    print(response)
