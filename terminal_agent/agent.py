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
        self.system_prompt_short = '''You are an AI terminal agent. Help the user with coding and terminal tasks in a Docker container. Be concise.

You have access to the following tools:
- create_python_file: Create a Python file in the Docker container.
- run_python_file: Run a Python file in the Docker container.
- list_files: List all the current files in the Docker container.

You can use these tools in succession to accomplish multi-step tasks (for example, create a file and then run it). After each tool call, you will receive the output and can decide on the next action, up to a maximum of 3 iterations per input. You may only call one tool at a time. Use the most recent tool output to inform your next tool call.

When using the `run_python_file` tool, you must only attempt to run files that actually exist in the container, as shown by the output of the `list_files` tool. Do not guess file names.

After you receive the output of a tool, if it answers the user's request, respond to the user in natural language. Only call another tool if more information or action is needed.

If the user asks to list files, call the `list_files` tool once, then respond to the user with the file list. Do not call any other tools unless the user requests further action.'''
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
        # Always keep the original user prompt
        original_prompt = {"role": "user", "content": user_input}
        tool_history = []  # Only tool call/response pairs for this session
        max_loops = 3
        loop_count = 0
        tool_outputs = []
        final_response_content = None

        while loop_count < max_loops:
            print(f"[DEBUG] Agentic loop iteration: {loop_count+1}")
            messages = [
                {"role": "system", "content": self.system_prompt},
                original_prompt,
                *tool_history
            ]
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
            if tool_calls:
                tool_call = tool_calls[0]
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                print(f"[DEBUG] Tool call: {function_name} with args: {function_args}")
                if function_name == "create_python_file":
                    function_response = self.create_python_file(
                        file_name=function_args.get("file_name"),
                        content=function_args.get("content")
                    )
                elif function_name == "run_python_file":
                    function_response = self.run_python_file(
                        file_name=function_args.get("file_name")
                    )
                elif function_name == "list_files":
                    function_response = self.list_files()
                    # Try to parse the output and format as a readable list
                    if isinstance(function_response, str):
                        files = [f for f in function_response.strip().splitlines() if f]
                    elif isinstance(function_response, list):
                        files = function_response
                    else:
                        files = []
                    formatted = "The following files are present in the Docker container:\n" + "\n".join(f"- {f}" for f in files)
                    tool_content = formatted
                else:
                    function_response = f"Unknown tool: {function_name}"
                    tool_content = str(function_response)

                if function_name != "list_files":
                    tool_content = str(function_response)

                tool_outputs.append({
                    "tool": function_name,
                    "args": function_args,
                    "output": tool_content
                })
                # Add this tool call/response to tool_history for next loop
                tool_history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_content
                })
                loop_count += 1

                # Reprompt the LLM after tool call to allow for normal response or further chaining
                messages = [
                    {"role": "system", "content": self.system_prompt},
                    original_prompt,
                    *tool_history
                ]
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
                    # LLM is done, return its message as the final answer
                    final_response_content = response_message.content
                    tool_history.append({
                        "role": "assistant",
                        "content": final_response_content
                    })
                    print(f"[DEBUG] LLM finished after tool call at iteration {loop_count}.")
                    break
                # Otherwise, continue chaining tools
                continue
            else:
                # No tool calls, just return the response as normal
                final_response_content = response_message.content
                print(f"[DEBUG] No tool calls. Exiting loop at iteration {loop_count+1}.")
                break

        if final_response_content is None:
            print(f"[DEBUG] Max loop count reached. Fetching final LLM response.")
            messages = [
                {"role": "system", "content": self.system_prompt},
                original_prompt,
                *tool_history
            ]
            response = self.groq.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                tools=self.tools,
                tool_choice="auto",
                max_completion_tokens=4096
            )
            final_response_content = response.choices[0].message.content
        # Fallback: if still no assistant message, return last tool output
        if final_response_content is None and tool_outputs:
            final_response_content = tool_outputs[-1]["output"]

        print(f"[DEBUG] Final response: {final_response_content}")
        return {
            "response_text": final_response_content,
            "docker_output": tool_outputs[-1]["output"] if tool_outputs else None,
            "all_tool_outputs": tool_outputs
        }