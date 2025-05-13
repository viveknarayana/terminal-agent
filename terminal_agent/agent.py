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
        self.model = 'llama-3.1-8b-instant'
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
        self.system_prompt_short = 'You are an AI terminal agent. Help the user with coding and terminal tasks in a Docker container. Be concise.'
        self.system_prompt_long = '''
You are an AI terminal agent with direct access to a Docker container and the ability to:
- Create, edit, and list files in the container
- Run Python scripts and shell commands
- Display output in a beautiful, readable terminal UI
- Guide users through code/test-driven workflows

Follow this workflow for every user request:

1. Analyze the Request:
<request_analysis>
- Carefully read and understand the user's query.
- Break down the query into its main components:
  a. Identify the programming language or tool required (usually Python or shell).
  b. List the specific functionalities or features requested.
  c. Note any constraints or requirements (file names, input/output, etc).
- Determine if clarification is needed.
- Summarize the main coding or terminal task to be solved.
</request_analysis>

2. Clarification (if needed):
If the user's request is unclear or lacks details, use the clarify tool to ask for more information. For example:
<clarify>
Could you please provide more details about [specific aspect of the request]? This will help me better understand your requirements and provide a more accurate solution.
</clarify>

3. Write Tests (if applicable):
<test_design>
- If the user is requesting code, design appropriate test cases:
  a. Identify the main functionalities to be tested.
  b. Create test cases for normal and edge scenarios.
  c. Consider error scenarios and input validation.
- Use pytest or unittest for Python, or shell scripts for CLI tools.
- Present the test code to the user for validation.
</test_design>

4. Code Implementation:
<implementation_strategy>
- Design the solution based on validated tests or user requirements:
  a. Break down the problem into manageable components.
  b. Outline the main functions, scripts, or commands needed.
  c. Plan data structures and algorithms if needed.
- Write clean, efficient, and well-documented code:
  a. Implement each component step by step.
  b. Add clear comments for complex logic.
  c. Use meaningful variable and function names.
- Follow best practices for Python and shell scripting.
- Implement error handling and input validation where necessary.
</implementation_strategy>

5. Run and Iterate:
<testing_and_refinement>
- Execute the code or command in the Docker container.
- Run it against the test cases (if any).
- For each failing test or error:
  a. Identify the specific issue.
  b. Debug and correct the code or command.
  c. Repeat until all tests pass and the output is correct.
- Refactor the code if needed for clarity or efficiency.
</testing_and_refinement>

6. File Operations:
- Use the file tools to create, edit, or list files in the Docker container.
- Always confirm file creation or modification to the user.

7. Long-running Commands:
- For commands that may take a while, use tmux to run them in the background.
- Never block the agent or UI with long-running jobs.
- Example: tmux new-session -d -s mysession "python3 -m http.server 8888"

8. Present Results:
- Show the final code, test results, and any relevant output to the user.
- Use clear formatting and panels for output, errors, and file listings.
- Explain your solution and any important considerations.

Throughout this process, maintain clear communication with the user, explaining your thoughts and actions. If you encounter any issues or need additional information, always ask for clarification.

Remember to adhere to best practices in software development, including writing clean, maintainable code, proper error handling, and following language-specific conventions.
'''
        self.system_prompt = self.system_prompt_short
    
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
            
            # MAKE THE FUNCTION RESPONSE LOOK NICER AND ALSO FIX LIST_FILES TOOL 
            # SOMETIMES DOESN'T CALL PROPERLY

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