import os
from dotenv import load_dotenv
from groq import Groq
from typing import List, Dict, Any

load_dotenv()

class AIAgent:
    def __init__(self):
        self.groq = Groq()
        self.model = 'llama-3.3-70b-versatile'
        self.tools = []
        #print("HELLO ", os.environ.get("ANTHROPIC_API_KEY"))
        # It should have its own conversation history in case I want to pass back
        self.conversation_history = []
        self.system_prompt = """You are a helpful terminal assistant with access to a Docker container.
        You can help users by having conversations and executing commands in the container when needed.
        When the user asks you to perform actions that require code execution, use the Docker environment. Otherwise,
        respond naturally with helpful information. """
    
    def add_message(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
    
    async def process_input(self, user_input: str):
        self.add_message("user", user_input)
        
        messages = [{"role": "system", "content": self.system_prompt}] + self.conversation_history

        response = self.groq.chat.completions.create(
            model=self.model, 
            messages=messages, 
            stream=False,
            tools=self.tools, # TO BE ADDED
            tool_choice="auto", # Lets GROQ decide when to use tool - implement routing later
            max_completion_tokens=4096 # Maximum number of tokens to allow in our response
        )

        response_message = response.choices[0].message.content
        self.add_message("assistant", response_message)
        
        
        return {
            "response_text": response_message
        }
    