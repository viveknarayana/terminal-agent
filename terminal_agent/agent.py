import os
from dotenv import load_dotenv
from groq import Groq
from typing import List, Dict, Any
import json
import subprocess
import logging

# Maybe convert to Cerebras for faster inference
# TO DO
# Do more prompt engineering to figure out how to improve context aware sequential tool calls 
# 'list files and make a python script to output those'
logging.basicConfig(
                level=logging.DEBUG,
                filename="agent_debug.log",
                filemode="a",
                format="%(asctime)s %(levelname)s %(message)s"
            )

load_dotenv()

class AIAgent:
    def __init__(self, docker_client):
        self.groq = Groq()
        # self.model = 'gemma2-9b-it'
        self.model = 'llama-3.3-70b-versatile'
        self.docker_client = docker_client

        # Get all MCP tools (summaries and full schema)
        self.mcp_tools = self.fetch_mcp_tools()
        self.mcp_tool_names = [tool["function"]["name"] for tool in self.mcp_tools]
        self.mcp_tool_summaries = [
            {"name": tool["function"]["name"], "description": tool["function"]["description"]}
            for tool in self.mcp_tools
        ]

        # Local tools:
        self.local_tools = [
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
            }
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "get_me",
            #         "description": "Get the authenticated user's GitHub profile information using MCP.",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {},
            #             "required": []
            #         }
            #     }
            # },
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "search_repositories",
            #         "description": "Search GitHub repositories using MCP.",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "query": {
            #                     "type": "string",
            #                     "description": "The search query for repositories."
            #                 },
            #                 "per_page": {
            #                     "type": "integer",
            #                     "description": "Results per page (default 20)",
            #                     "default": 20
            #                 },
            #                 "page": {
            #                     "type": "integer",
            #                     "description": "Page number (default 1)",
            #                     "default": 1
            #                 }
            #             },
            #             "required": ["query"]
            #         }
            #     }
            # }
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
        self.tools = self.local_tools + self.mcp_tools
        self.tool_summaries = [
            {"name": tool["function"]["name"], "description": tool["function"]["description"]}
            for tool in self.tools
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

    # def get_me(self):
    #     token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    #     if not token:
    #         return "[ERROR] GITHUB_PERSONAL_ACCESS_TOKEN not set."
    #     return self.call_mcp_stdio_tool("get_me", arguments={}, docker_token=token)

    # def search_repositories(self, query, per_page=20, page=1):
    #     token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    #     if not token:
    #         return "[ERROR] GITHUB_PERSONAL_ACCESS_TOKEN not set."
    #     params = {"query": query, "perPage": per_page, "page": page}
    #     return self.call_mcp_stdio_tool("search_repositories", arguments=params, docker_token=token)

    def log_all_mcp_tools(self):

        token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            logging.debug("[ERROR] GITHUB_PERSONAL_ACCESS_TOKEN not set.")
            return
        proc = subprocess.Popen(
            [
                "docker", "run", "-i", "--rm",
                "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={token}",
                "ghcr.io/github/github-mcp-server"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        response_line = proc.stdout.readline()
        try:
            response = json.loads(response_line)
        except Exception as e:
            response = {"error": f"Failed to parse response: {response_line}", "exception": str(e)}
        proc.terminate()
        logging.debug(f"MCP tools/list response: {response}")

    def fetch_mcp_tools(self):
        token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            logging.debug("[ERROR] GITHUB_PERSONAL_ACCESS_TOKEN not set.")
            return []
        proc = subprocess.Popen(
            [
                "docker", "run", "-i", "--rm",
                "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={token}",
                "ghcr.io/github/github-mcp-server"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        response_line = proc.stdout.readline()
        try:
            response = json.loads(response_line)
            proc.terminate()
            if "result" in response and "tools" in response["result"]:
                return [
                    {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool.get("inputSchema", {})
                        }
                    }
                    for tool in response["result"]["tools"]
                ]
            else:
                logging.debug(f"Unexpected MCP tools/list response: {response}")
                return []
        except Exception as e:
            proc.terminate()
            logging.debug(f"Failed to parse MCP tools/list response: {response_line}, error: {e}")
            return []

    def select_tool(self, user_input):
        tool_list_str = "\n".join(
            f"{i+1}. {t['name']}: {t['description']}" for i, t in enumerate(self.tool_summaries)
        )
        prompt = (
            f"User request: {user_input}\n"
            f"Available tools:\n{tool_list_str}\n"
            "If one of these tools is relevant, reply ONLY with the tool name. "
            "If none are relevant, reply with 'none' and answer the user's question in natural language."
        )
        response = self.groq.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=128
        )
        content = response.choices[0].message.content.strip()
        if content.lower().startswith("none"):
            return None, content[4:].strip()  # NLP answer
        return content, None

    async def process_input(self, user_input: str):
        original_prompt = {"role": "user", "content": user_input}
        self.add_message("user", user_input)
        tool_outputs = []
        max_loops = 3
        loop_count = 0
        last_tool_output = None
        current_input = user_input
        
        while loop_count < max_loops:
            # Select tool for the current input (which may include previous tool output)
            chosen_tool_name, nl_response = self.select_tool(current_input)
            if nl_response is not None:
                self.add_message("assistant", nl_response)
                yield {"type": "text", "response": nl_response}
                return
            if not chosen_tool_name:
                # No tool found, return last tool output if any
                if last_tool_output is not None:
                    yield {"type": "tool", "tool": tool_outputs[-1]["tool"], "args": tool_outputs[-1]["args"], "output": last_tool_output}
                else:
                    yield {"type": "text", "response": "[No relevant tool found and no response generated.]"}
                return
            selected_tool = next((tool for tool in self.tools if tool["function"]["name"] == chosen_tool_name), None)
            if not selected_tool:
                yield {"type": "text", "response": f"[Tool '{chosen_tool_name}' not found in available tools.]"}
                return

            # Prepare messages for the LLM, including all conversation history and tool outputs
            messages = [*self.conversation_history, {"role": "system", "content": self.system_prompt}, {"role": "user", "content": current_input}]
            response = self.groq.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                tools=[selected_tool],
                tool_choice="auto",
                max_completion_tokens=4096
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            if not tool_calls:
                # If no tool call, treat as final response
                self.add_message("assistant", response_message.content)
                yield {"type": "text", "response": response_message.content}
                return
            tool_call = tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            # Run the tool (local or MCP)
            if chosen_tool_name in [t["function"]["name"] for t in self.local_tools]:
                if chosen_tool_name == "create_python_file":
                    tool_result = self.create_python_file(
                        file_name=function_args.get("file_name"),
                        content=function_args.get("content")
                    )
                elif chosen_tool_name == "run_python_file":
                    tool_result = self.run_python_file(
                        file_name=function_args.get("file_name")
                    )
                elif chosen_tool_name == "list_files":
                    tool_result = self.list_files()
                    if isinstance(tool_result, str):
                        files = [f for f in tool_result.strip().splitlines() if f]
                    elif isinstance(tool_result, list):
                        files = tool_result
                    else:
                        files = []
                    tool_result = "The following files are present in the Docker container:\n" + "\n".join(f"- {f}" for f in files)
                elif chosen_tool_name == "install_dependency":
                    tool_result = self.install_dependency(
                        dependency=function_args.get("dependency")
                    )
                else:
                    tool_result = f"Unknown local tool: {chosen_tool_name}"
            else:
                tool_result = self.call_mcp_stdio_tool(
                    tool_name=tool_call.function.name,
                    arguments=function_args,
                    docker_token=os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
                )
            # Accumulate tool output
            tool_outputs.append({"tool": chosen_tool_name, "args": function_args, "output": tool_result})
            last_tool_output = tool_result
            # Add tool output to conversation history as assistant message
            self.add_message("assistant", f"Tool '{chosen_tool_name}' output: {tool_result}")
            # Prepare next input: user request + all tool outputs so far
            current_input = f"User request: {user_input}\nPrevious tool outputs: {tool_result}"
            loop_count += 1
            # If the model should stop (e.g., no more tool calls), check in next loop
        # If max_loops reached, return last tool output
        if tool_outputs:
            yield {"type": "tool", "tool": tool_outputs[-1]["tool"], "args": tool_outputs[-1]["args"], "output": tool_outputs[-1]["output"]}
        else:
            yield {"type": "text", "response": "[No relevant tool found and no response generated.]"}
        return

    async def process_input_stream(self, user_input: str):
        async for event in self.process_input(user_input):
            yield event