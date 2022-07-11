from getpass import getpass
import requests

from .project import Project
from .exception import MIQAAPIError


class MIQA:
    """
    Attributes:
      url, headers, token, version,
      projects, artifact_options
    Functions:
      login, get_config,
      get_all_objects, get_project_by_id, create_project,
      print_all_objects
    """

    def __init__(self, url, username=None, password=None):
        if not username:
            username = input("MIQA username: ")
        if not password:
            password = getpass(f"Enter MIQA password for {username}")
        self.url = url.rstrip("/")
        if "/api" not in self.url:
            self.url += "/api/v1"
        self.headers = {
            "Accept": "application/json",
        }
        self.projects = []
        self.login(username, password)
        self.get_config()

    def login(self, username, password):
        auth_url = self.url.replace("/api/v1", "/api-token-auth/")
        response = requests.post(
            auth_url,
            data={
                "username": username,
                "password": password,
            },
        )
        if response.status_code != 200:
            raise MIQAAPIError("Invalid username or password provided")
        self.token = response.json()["token"]
        self.headers["Authorization"] = f"Token {self.token}"

    def get_config(self):
        response = requests.get(f"{self.url}/configuration", headers=self.headers).json()
        self.version = response["version"]
        self.artifact_options = response["artifact_options"]
        return response

    def get_all_objects(self):
        api_path = "projects"
        response = requests.get(f"{self.url}/{api_path}", headers=self.headers)
        response.raise_for_status()
        self.projects = [Project(**result, MIQA=self) for result in response.json()["results"]]
        return self.projects

    def get_project_by_id(self, id: str):
        if self.projects:
            matches = [proj for proj in self.projects if proj.id == id]
            if len(matches) == 1:
                return matches[0]
        response = requests.get(f"{self.url}/projects/{id}", headers=self.headers).json()
        if response.status_code == 404:
            return None
        new_project = Project(**response, MIQA=self)
        self.projects.append(new_project)
        return new_project

    def create_project(self, name: str):
        api_path = "projects"
        response = requests.post(
            f"{self.url}/{api_path}",
            headers=self.headers,
            json={
                'name': name,
            },
        )
        response.raise_for_status()
        new_project = Project(**dict(response.json(), MIQA=self))
        self.projects.append(new_project)
        return new_project

    def print_all_objects(self, indent=0):
        if len(self.projects) < 1:
            self.get_all_objects()
        print(" " * indent, str(self))
        for proj in self.projects:
            proj.print_all_objects(indent=indent)

    def __repr__(self):
        return f"MIQA Instance {self.url}"
