from getpass import getpass
import requests

from project import Project


class MIQA:
    """
    Attributes:
      url, headers, token, version,
      projects,
    Functions:
      login, get_config, get_all_projects, get_project_by_id,
      list_all_objects
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
            raise Exception("Invalid username or password provided")
        self.token = response.json()["token"]
        self.headers["Authorization"] = f"Token {self.token}"

    def get_config(self):
        content = requests.get(f"{self.url}/configuration", headers=self.headers).json()
        self.version = content["version"]
        return content

    def get_all_projects(self):
        content = requests.get(f"{self.url}/projects", headers=self.headers).json()
        self.projects = [Project(**result) for result in content["results"]]
        return self.projects

    def get_project_by_id(self, id: str):
        if self.projects:
            matches = [proj for proj in self.projects if proj.id == id]
            if len(matches) == 1:
                return matches[0]
        content = requests.get(f"{self.url}/projects/{id}", headers=self.headers).json()
        self.projects.append(Project(**content))
        return self.projects[-1]

    def list_all_objects(self, indent=0):
        if len(self.projects) < 1:
            self.get_all_projects()
        print(" " * indent, str(self))
        for proj in self.projects:
            proj.list_all_objects(indent=indent)

    def __repr__(self):
        return f"MIQA Instance {self.url}"
