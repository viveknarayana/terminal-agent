import docker
import os

class DockerExecution:

    def __init__(self, baseURL):
        self.client = docker.DockerClient(base_url=baseURL)
        self.container = None

    def create_container(self):
        # Code to create Docker container which Python will run on
        # Assign self.container to container
        pass

    def copy_file(self, source_path):
        # Code to copy test.py to container
        pass
    
    def run_file(self, file_name):
        # Code to run test.py inside the container
        # Call when receive command from Terminal Interaction
        pass

    def end_container(self):
        pass