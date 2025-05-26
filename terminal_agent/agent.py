import os
from dotenv import load_dotenv
from groq import Groq
from typing import List, Dict, Any
import json
import logging

# Maybe convert to Cerebras for faster inference
# TO DO
# Do more prompt engineering to figure out how to improve context aware sequential tool calls 
# 'list files and make a python script to output those'


load_dotenv()

class AIAgent:
    def __init__(self, docker_client):
        self.groq = Groq()
        self.model = 'gemma2-9b-it'
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
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "install_dependency",
                    "description": "Install a Python dependency in the Docker container using pip.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dependency": {
                                "type": "string",
                                "description": "The name of the dependency to install, e.g., 'pandas' or 'numpy==1.25.0'"
                            }
                        },
                        "required": ["dependency"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_me",
                    "description": "Get the authenticated user's GitHub profile information using MCP.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_repositories",
                    "description": "Search GitHub repositories using MCP.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query for repositories."
                            },
                            "per_page": {
                                "type": "integer",
                                "description": "Results per page (default 20)",
                                "default": 20
                            },
                            "page": {
                                "type": "integer",
                                "description": "Page number (default 1)",
                                "default": 1
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "run_shell_command",
            #         "description": "Run a shell command inside the Docker container.",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "command": {
            #                     "type": "string",
            #                     "description": "The shell command to run, e.g., 'ls -l' or 'cat requirements.txt'"
            #                 }
            #             },
            #             "required": ["command"]
            #         }
            #     }
            # }
        ]
    
        self.conversation_history = []
        self.system_prompt_short = '''You are an AI terminal agent. You can call tools in succession to accomplish multi-step user requests in a Docker container. For each user request, decide if you should call a tool or respond with text. If the request requires multiple actions, call the necessary tools one after another until all steps are complete, then respond with text. Remember to only call one tool per request. Only respond with text when you are done with all tool calls needed for the user's request.'''
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

    def install_dependency(self, dependency):
        if self.docker_client:
            try:
                return self.docker_client.install_dependency(dependency)
            except Exception as e:
                return f"Error: {str(e)}"
        return "Docker client not available."

    # def run_shell_command(self, command):
    #     if self.docker_client:
    #         try:
    #             return self.docker_client.run_shell_command(command)
    #         except Exception as e:
    #             return f"Error: {str(e)}"
    #     return "Docker client not available."

    def call_mcp_stdio_tool(self, tool_name, arguments=None, docker_token=None):
        import subprocess
        import json
        if arguments is None:
            arguments = {}
        if docker_token is None:
            raise ValueError("You must provide a GitHub token for MCP server.")
        proc = subprocess.Popen(
            [
                "docker", "run", "-i", "--rm",
                "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={docker_token}",
                "ghcr.io/github/github-mcp-server"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        response_line = proc.stdout.readline()
        try:
            response = json.loads(response_line)
        except Exception as e:
            response = {"error": f"Failed to parse response: {response_line}", "exception": str(e)}
        proc.terminate()
        return response

    def get_me(self):
        token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            return "[ERROR] GITHUB_PERSONAL_ACCESS_TOKEN not set."
        return self.call_mcp_stdio_tool("get_me", arguments={}, docker_token=token)

    def search_repositories(self, query, per_page=20, page=1):
        token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            return "[ERROR] GITHUB_PERSONAL_ACCESS_TOKEN not set."
        params = {"query": query, "perPage": per_page, "page": page}
        return self.call_mcp_stdio_tool("search_repositories", arguments=params, docker_token=token)

    async def process_input(self, user_input: str):
        original_prompt = {"role": "user", "content": user_input}
        self.add_message("user", user_input)
        tool_outputs = []
        max_loops = 3
        loop_count = 0
        last_tool_name = None
        last_tool_args = None
        last_tool_output = None
        available_tools = [tool["function"]["name"] for tool in self.tools]
        
        # First LLM call: just the user prompt
        messages = [
            *self.conversation_history,
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
                self.add_message("assistant", response_message.content)
                yield {"type": "text", "response": response_message.content}
                return
            # Model chose a tool
            tool_call = tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
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
                elif tool_name == "install_dependency":
                    return (
                        isinstance(args, dict)
                        and isinstance(args.get("dependency"), str) and args.get("dependency")
                    )
                elif tool_name == "get_me":
                    return True  # No args required
                elif tool_name == "search_repositories":
                    return (
                        isinstance(args, dict)
                        and isinstance(args.get("query"), str) and args.get("query")
                    )
                elif tool_name == "run_shell_command":
                    return (
                        isinstance(args, dict)
                        and isinstance(args.get("command"), str) and args.get("command")
                    )
                return False

            if not valid_tool_args(function_name, function_args):
                error_msg = f"[ERROR] Invalid arguments for tool '{function_name}': {function_args}"
                print(error_msg)
                yield {"type": "text", "response": error_msg}
                return
            # Prevent repeated tool calls with same arguments
            if last_tool_name == function_name and last_tool_args == function_args:
                repeat_msg = f"[Agent stopped: repeated tool call '{function_name}' with same arguments] {last_tool_output}"
                print(f"[DEBUG] {repeat_msg}")
                return
            last_tool_name = function_name
            last_tool_args = function_args
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
            elif function_name == "install_dependency":
                tool_result = self.install_dependency(
                    dependency=function_args.get("dependency")
                )
            elif function_name == "get_me":
                tool_result = self.get_me()
            elif function_name == "search_repositories":
                tool_result = self.search_repositories(
                    query=function_args.get("query"),
                    per_page=function_args.get("per_page", 20),
                    page=function_args.get("page", 1)
                )
            elif function_name == "run_shell_command":
                tool_result = self.run_shell_command(
                    command=function_args.get("command")
                )
            else:
                tool_result = f"Unknown tool: {function_name}"
            last_tool_output = tool_result
            tool_outputs.append({
                "tool": function_name,
                "args": function_args,
                "output": tool_result
            })
            yield {"type": "tool", "tool": function_name, "args": function_args, "output": tool_result}
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
            messages.append(tool_call_msg)
            messages.append(tool_output_msg)
            loop_count += 1
            print(f"[DEBUG] Tool call: {function_name} with args: {function_args}")
            print(f"[DEBUG] Tool output: {tool_result}")
            logging.basicConfig(
                level=logging.DEBUG,
                filename="agent_debug.log",
                filemode="a",
                format="%(asctime)s %(levelname)s %(message)s"
            )
            logging.debug(tool_calls)
        # If we hit max_loops, return last tool output
        yield {"type": "text", "response": f"[Agent stopped after {max_loops} tool calls] {last_tool_output}"}
        return

    async def process_input_stream(self, user_input: str):
        async for event in self.process_input(user_input):
            yield event