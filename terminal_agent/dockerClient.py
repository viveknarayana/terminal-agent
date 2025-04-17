import docker
import os

# Create Docker client object in UI for agentic loop

class DockerExecution:

    def __init__(self):
        self.client = client = docker.from_env()
        self.container = None

    def start_container(self):
        # checks if already exists
        try:
            existing_container = self.client.containers.get("terminal-agent-container")
            
            if existing_container.status == "running":
                self.container = existing_container
            else:
                print("Container exists but is not running. Removing and creating a new one.")
                existing_container.remove(force=True)
                self.container = self.client.containers.run(
                    image="python:3.10-slim",
                    command="sleep infinity",
                    detach=True,
                    tty=True,
                    name="terminal-agent-container"
                )
        except docker.errors.NotFound:
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
        
        # base64 fixed quotation issues
        import base64
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        # Create the file using base64 decoding because it didn't work without for some reason
        cmd = f'bash -c "echo {encoded_content} | base64 -d > {file_path}"'
        exit_code, output = self.container.exec_run(cmd)
        
        if exit_code != 0:
            raise RuntimeError(f"Failed to write file: {output.decode('utf-8')}")
        
        return 
    
    def run_file(self, file_name):
        if not self.container:
            raise RuntimeError("Container not started. Call start_container() first.")
        
        if file_name.endswith('.py'):
            cmd = f"python {file_name}"
        else:
            cmd = f"./{file_name}"
        
        exit_code, output = self.container.exec_run(cmd)
        
        return {
            'exit_code': exit_code,
            'output': output.decode('utf-8')
        }

    def end_container(self):
        pass