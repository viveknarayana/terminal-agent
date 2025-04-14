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

    def write_file(self, file_path, content):
        if not self.container:
            raise RuntimeError("Container not started. Call start_container() first.")

        cmd = f'sh -c "cat > {file_path}"'
        _, socket = self.container.exec_run(
            cmd, stdin=True, stdout=True, stderr=True, stream=False, socket=True
        )
        socket._sock.sendall((content + "\n").encode("utf-8"))
        socket._sock.close()
    
    def run_file(self, file_name):
        # Code to run test.py inside the container
        # Call when receive command from Terminal Interaction
        pass

    def end_container(self):
        pass