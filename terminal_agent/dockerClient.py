import docker
import os

# Create Docker client object in UI for agentic loop

class DockerExecution:

    def __init__(self, baseURL):
        self.client = client = docker.from_env()
        self.container = None

    def start_container(self):
        self.container = self.client.containers.run(
            image="python:3.10-slim",
            command="sleep infinity",
            detach=True,
            tty=True,
            name="terminal-agent-container"
        )

        # Add tool to install dependencies as well

    def copy_file(self, source_path):
        # Code to copy test.py to container
        pass
    
    def run_file(self, file_name):
        # Code to run test.py inside the container
        # Call when receive command from Terminal Interaction
        pass

    def end_container(self):
        pass