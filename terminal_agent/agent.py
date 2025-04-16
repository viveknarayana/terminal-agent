import os
from dotenv import load_dotenv
from anthropic import Anthropic
from typing import List, Dict, Any

load_dotenv()

class AIAgent:
    def __init__(self):
        self.anthropic = Anthropic()
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

        response = self.anthropic.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=2000,
            messages=messages
        )
        
        content = response.content[0].text
        self.add_message("assistant", content)
        
        
        return {
            "response_text": content
        }
    