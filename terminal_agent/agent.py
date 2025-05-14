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

If the user requests running multiple files, call the appropriate tool for each file, one at a time, until all requested files have been processed.
'''
        self.system_prompt_short = '''You are an AI terminal agent. You can call tools in succession to accomplish multi-step user requests in a Docker container. For each user request, decide if you should call a tool or respond with text. If the request requires multiple actions, call the necessary tools one after another until all steps are complete, then respond with text. Only respond with text when you are done with all tool calls needed for the user's request.'''
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
        original_prompt = {"role": "user", "content": user_input}
        tool_outputs = []
        max_loops = 5
        loop_count = 0
        last_tool_name = None
        last_tool_args = None
        last_tool_output = None
        
        # First LLM call: just the user prompt
        messages = [
            {"role": "system", "content": self.system_prompt},
            original_prompt
        ]
        while loop_count < max_loops:
            response = self.groq.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                tools=self.tools,
                tool_choice="auto",
                max_completion_tokens=4096
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            if not tool_calls:
                # Model chose to respond with text
                return {
                    "response_text": response_message.content,
                    "docker_output": last_tool_output,
                    "all_tool_outputs": tool_outputs
                }
            # Model chose a tool
            tool_call = tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            last_tool_name = function_name
            last_tool_args = function_args
            # Validate tool arguments before calling the tool
            def valid_tool_args(tool_name, args):
                if tool_name == "create_python_file":
                    return (
                        isinstance(args, dict)
                        and isinstance(args.get("file_name"), str) and args.get("file_name")
                        and isinstance(args.get("content"), str)
                    )
                elif tool_name == "run_python_file":
                    return (
                        isinstance(args, dict)
                        and isinstance(args.get("file_name"), str) and args.get("file_name")
                    )
                elif tool_name == "list_files":
                    return True  # No args required
                return False

            if not valid_tool_args(function_name, function_args):
                error_msg = f"[ERROR] Invalid arguments for tool '{function_name}': {function_args}"
                print(error_msg)
                return {
                    "response_text": error_msg,
                    "docker_output": last_tool_output,
                    "all_tool_outputs": tool_outputs
                }
            # Prevent repeated tool calls with same arguments
            if len(tool_outputs) > 0 and function_name == tool_outputs[-1]["tool"] and function_args == tool_outputs[-1]["args"]:
                repeat_msg = f"[Agent stopped: repeated tool call '{function_name}' with same arguments] {last_tool_output}"
                print(f"[DEBUG] {repeat_msg}")
                return {
                    "response_text": repeat_msg,
                    "docker_output": last_tool_output,
                    "all_tool_outputs": tool_outputs
                }
            # Actually call the tool
            if function_name == "create_python_file":
                tool_result = self.create_python_file(
                    file_name=function_args.get("file_name"),
                    content=function_args.get("content")
                )
            elif function_name == "run_python_file":
                tool_result = self.run_python_file(
                    file_name=function_args.get("file_name")
                )
            elif function_name == "list_files":
                tool_result = self.list_files()
                if isinstance(tool_result, str):
                    files = [f for f in tool_result.strip().splitlines() if f]
                elif isinstance(tool_result, list):
                    files = tool_result
                else:
                    files = []
                tool_result = "The following files are present in the Docker container:\n" + "\n".join(f"- {f}" for f in files)
            else:
                tool_result = f"Unknown tool: {function_name}"
            last_tool_output = tool_result
            tool_outputs.append({
                "tool": function_name,
                "args": function_args,
                "output": tool_result
            })
            # Prepare next LLM call: original prompt, tool call, tool output
            tool_call_msg = {
                "role": "assistant",
                "content": f"TOOL CALL: {function_name} with args: {json.dumps(function_args)}"
            }
            tool_output_msg = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": str(tool_result)
            }
            messages = [
                {"role": "system", "content": self.system_prompt},
                original_prompt,
                tool_call_msg,
                tool_output_msg
            ]
            loop_count += 1
            print(f"[DEBUG] Tool call: {function_name} with args: {function_args}")
            print(f"[DEBUG] Tool output: {tool_result}")
        # If we hit max_loops, return last tool output
        return {
            "response_text": f"[Agent stopped after {max_loops} tool calls] {last_tool_output}",
            "docker_output": last_tool_output,
            "all_tool_outputs": tool_outputs
        }