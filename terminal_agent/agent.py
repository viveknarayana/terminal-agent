import os
from dotenv import load_dotenv
from groq import Groq
from typing import List, Dict, Any
import json

# Maybe convert to Cerebras for faster inference

load_dotenv()

class AIAgent:
    def __init__(self, docker_client):
        self.groq = Groq()
        self.model = 'llama-3.3-70b-versatile'
        self.docker_client = docker_client
        
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_python_file",
                    "description": "Create a Python file in the Docker container",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_name": {
                                "type": "string",
                                "description": "Name of the Python file to create (e.g., 'test.py')"
                            },
                            "content": {
                                "type": "string",
                                "description": "Python code content to write to the file"
                            }
                        },
                        "required": ["file_name", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_python_file",
                    "description": "Run a Python file in the Docker container",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_name": {
                                "type": "string",
                                "description": "Name of the Python file to run (e.g., 'test.py')"
                            }
                        },
                        "required": ["file_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List all the current files in the Docker container",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [""]
                    }
                }
            }
        ]
    
        self.conversation_history = []
        self.system_prompt = """You are a helpful terminal assistant with access to a Docker container.
        You can help users by having conversations and executing commands in the container when needed.
        When the user asks you to create Python files, use the create_python_file tool to write the code to the Docker container.
        After creating a Python file, you can run it using the run_python_file tool to execute the code and see the output.
        
        For example, if a user asks you to create and run a simple hello world script, you can:
        1. Use create_python_file to write a Python file with print("Hello World")
        2. Use run_python_file to execute the script and show the output"""
    
    def add_message(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
    
    # TOOL DEFINITIONS - uses dockerClient tools
    def list_files(self):
        if self.docker_client:
            try:
                files = self.docker_client.list_files()
                return files
            except Exception as e:
                return f"Error: {str(e)}"
        return "Docker client not available."

    def create_python_file(self, file_name, content):
        if self.docker_client:
            try:
                self.docker_client.write_file(f"{file_name}", content)
                return f"File {file_name} created successfully"
            except Exception as e:
                return f"Error: {str(e)}"
        return "Docker client not available."
    
    def run_python_file(self, file_name):
        if self.docker_client:
            try: 
                output = self.docker_client.run_file(file_name)
                return output
            except Exception as e:
                return f"Error: {str(e)}"
        return "Docker client not available."

    
    async def process_input(self, user_input: str):
        self.add_message("user", user_input)
        
        messages = [{"role": "system", "content": self.system_prompt}] + self.conversation_history

        response = self.groq.chat.completions.create(
            model=self.model, 
            messages=messages, 
            stream=False,
            tools=self.tools,
            tool_choice="auto",
            max_completion_tokens=4096
        )

        response_message = response.choices[0].message
        
        # Process tool calls if any
        tool_calls = response_message.tool_calls
        
        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "create_python_file":
                    function_response = self.create_python_file(
                        file_name=function_args.get("file_name"),
                        content=function_args.get("content")
                    )
                    
                    self.conversation_history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response
                    })
                elif function_name == "run_python_file":
                    function_response = self.run_python_file(
                        file_name=function_args.get("file_name")
                    )
                    
                    self.conversation_history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response)
                    })
                elif function_name == "list_files":
                    function_response = self.list_files()
                    
                    self.conversation_history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response)
                    })
            
            # Get final response after tool use if any data was fetched
            second_response = self.groq.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.system_prompt}] + self.conversation_history
            )
            
            response_content = second_response.choices[0].message.content
            self.add_message("assistant", response_content)
            
            return {
                "response_text": response_content,
                "docker_output": function_response if tool_calls else None
            }
        else:
            # No tool calls, just return the response
            self.add_message("assistant", response_message.content)
            return {
                "response_text": response_message.content,
                "docker_output": None
            }