import httpx
from typing import Optional, Dict, List

from fastapi import Request, HTTPException
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class FrameworkDetector:
    """
    Detect project framework based on repository files
    """

    # Список всех поддерживаемых фреймворков
    SUPPORTED_FRAMEWORKS = [
        "FastAPI", "Flask", "Django",  # Python
        "Next.js", "React", "Vue.js", "Angular", "Express", "Nest.js",  # JavaScript/TypeScript
        "Spring Boot", "Micronaut", "Quarkus",  # Java
        "Go Fiber", "Gin", "Echo",  # Go
        "Ruby on Rails", "Sinatra",  # Ruby
        "Laravel", "Symfony",  # PHP
        ".NET", "ASP.NET Core",  # C#
        "Docker"  # Containerized
    ]

    FRAMEWORK_SIGNATURES = {
        # Python frameworks
        "FastAPI": {
            "files": ["requirements.txt", "setup.py", "Pipfile", "pyproject.toml"],
            "patterns": ["fastapi", "FastAPI"]
        },
        "Flask": {
            "files": ["requirements.txt", "setup.py", "Pipfile", "pyproject.toml"],
            "patterns": ["flask", "Flask"]
        },
        "Django": {
            "files": ["requirements.txt", "setup.py", "Pipfile", "pyproject.toml", "manage.py"],
            "patterns": ["django", "Django"]
        },

        # JavaScript/TypeScript frameworks
        "Next.js": {
            "files": ["package.json"],
            "patterns": ['"next":', '"dependencies".*"next":']
        },
        "React": {
            "files": ["package.json"],
            "patterns": ['"react":', '"dependencies".*"react":']
        },
        "Vue.js": {
            "files": ["package.json"],
            "patterns": ['"vue":', '"dependencies".*"vue":']
        },
        "Angular": {
            "files": ["package.json", "angular.json"],
            "patterns": ['"@angular/core":', '"angular"']
        },
        "Express": {
            "files": ["package.json"],
            "patterns": ['"express":']
        },
        "Nest.js": {
            "files": ["package.json"],
            "patterns": ['"@nestjs/core":']
        },

        # Go frameworks
        "Go Fiber": {
            "files": ["go.mod"],
            "patterns": ["github.com/gofiber/fiber"]
        },
        "Gin": {
            "files": ["go.mod"],
            "patterns": ["github.com/gin-gonic/gin"]
        },
        "Echo": {
            "files": ["go.mod"],
            "patterns": ["github.com/labstack/echo"]
        },

        # Java frameworks
        "Spring Boot": {
            "files": ["pom.xml", "build.gradle"],
            "patterns": ["spring-boot", "springframework"]
        },
        "Micronaut": {
            "files": ["pom.xml", "build.gradle"],
            "patterns": ["micronaut"]
        },
        "Quarkus": {
            "files": ["pom.xml", "build.gradle"],
            "patterns": ["quarkus"]
        },

        # Ruby frameworks
        "Ruby on Rails": {
            "files": ["Gemfile"],
            "patterns": ["rails", "gem 'rails'"]
        },
        "Sinatra": {
            "files": ["Gemfile"],
            "patterns": ["sinatra", "gem 'sinatra'"]
        },

        # PHP frameworks
        "Laravel": {
            "files": ["composer.json"],
            "patterns": ["laravel/framework"]
        },
        "Symfony": {
            "files": ["composer.json"],
            "patterns": ["symfony/symfony", "symfony/framework-bundle"]
        },

        # .NET frameworks
        ".NET": {
            "files": [".csproj"],
            "patterns": ["<Project"]
        },
        "ASP.NET Core": {
            "files": [".csproj"],
            "patterns": ["Microsoft.AspNetCore"]
        },

        # Docker
        "Docker": {
            "files": ["Dockerfile", "docker-compose.yml"],
            "patterns": ["FROM", "version:"]
        }
    }
    
    

    def __init__(self, github_token: str):
        self.github_token = github_token

    async def detect_framework(self, project_id: str, repo_full_name: str, folder_path: str = "") -> Dict:
        """
        Detect framework for a GitHub repository

        Args:
            repo_full_name: Full repository name (e.g., "owner/repo")
            folder_path: Path to folder within repository (empty string = root)

        Returns:
            Dict with detected frameworks and metadata
        """
        detected_frameworks = []
        repository_files = await self._get_repository_files(repo_full_name, folder_path)

        if not repository_files:
            return {
                "project_id": project_id,
                "repo": repo_full_name,
                "frameworks": [],
                "primary_framework": None,
                "language": None,
                "has_dockerfile": False,
                "folder_path": folder_path
            }

        for framework, signature in self.FRAMEWORK_SIGNATURES.items():
            if await self._check_framework(repo_full_name, signature, repository_files, folder_path):
                detected_frameworks.append(framework)

        primary_framework = self._determine_primary_framework(detected_frameworks)

        language = await self._get_repo_language(repo_full_name)

        has_dockerfile = "Dockerfile" in repository_files or "docker-compose.yml" in repository_files

        return {
            
            "project_id": project_id,
            "repo": repo_full_name,
            "frameworks": detected_frameworks,
            "primary_framework": primary_framework,
            "language": language,
            "has_dockerfile": has_dockerfile,
            "buildpack": self._get_buildpack(primary_framework, language),
            "folder_path": folder_path
        }

    async def _get_repository_files(self, repo_full_name: str, folder_path: str = "") -> List[str]:
        """Get list of files in repository at specified path"""
        # Build URL with folder path if provided
        if folder_path:
            url = f"https://api.github.com/repos/{repo_full_name}/contents/{folder_path}"
        else:
            url = f"https://api.github.com/repos/{repo_full_name}/contents"

        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                contents = response.json()

                # Get file names
                files = [item["name"] for item in contents if item["type"] == "file"]
                return files
        except Exception as e:
            print(f"Error fetching repository files from {folder_path or 'root'}: {e}")
            return []

    async def _check_framework(self, repo_full_name: str, signature: Dict, repo_files: List[str], folder_path: str = "") -> bool:
        """Check if framework signature matches"""
        # Check if required files exist
        has_required_file = False
        for file_pattern in signature["files"]:
            if file_pattern.endswith(".*"):
                # Check for file extension pattern
                ext = file_pattern.split(".")[-1]
                if any(f.endswith(f".{ext}") for f in repo_files):
                    has_required_file = True
                    break
            elif file_pattern in repo_files:
                has_required_file = True
                break

        if not has_required_file:
            return False

        # Check file content for patterns
        for file_name in signature["files"]:
            if file_name in repo_files:
                content = await self._get_file_content(repo_full_name, file_name, folder_path)
                if content:
                    for pattern in signature["patterns"]:
                        if pattern.lower() in content.lower():
                            return True

        return False

    async def _get_file_content(self, repo_full_name: str, file_name: str, folder_path: str = "") -> Optional[str]:
        """Get content of a specific file"""
        # Build file path
        if folder_path:
            file_path = f"{folder_path}/{file_name}"
        else:
            file_path = file_name

        url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.raw",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Error fetching file {file_path}: {e}")
            return None

    async def _get_repo_language(self, repo_full_name: str) -> Optional[str]:
        """Get primary language of repository"""
        url = f"https://api.github.com/repos/{repo_full_name}"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                repo_data = response.json()
                return repo_data.get("language")
        except Exception as e:
            print(f"Error fetching repository language: {e}")
            return None

    def _determine_primary_framework(self, frameworks: List[str]) -> Optional[str]:
        """Determine the primary framework from detected frameworks"""
        # Priority order for frameworks (more specific first)
        priority = [
            "Next.js", "Nest.js", "Django", "FastAPI", "Spring Boot", "Quarkus", "Micronaut",
            "Ruby on Rails", "Laravel", "Symfony", "ASP.NET Core",
            "Flask", "Express", "Sinatra", "Go Fiber", "Gin", "Echo",
            "React", "Vue.js", "Angular", ".NET"
        ]

        for framework in priority:
            if framework in frameworks:
                return framework

        return frameworks[0] if frameworks else None

    def _get_buildpack(self, framework: Optional[str], language: Optional[str]) -> str:
        """Determine buildpack based on framework and language"""
        if not framework and not language:
            return "heroku/buildpacks:20"

        # Map framework/language to buildpack
        buildpack_map = {
            # Python
            "FastAPI": "heroku/python",
            "Flask": "heroku/python",
            "Django": "heroku/python",

            # Node.js/JavaScript
            "Next.js": "heroku/nodejs",
            "React": "heroku/nodejs",
            "Vue.js": "heroku/nodejs",
            "Angular": "heroku/nodejs",
            "Express": "heroku/nodejs",
            "Nest.js": "heroku/nodejs",

            # Java
            "Spring Boot": "heroku/java",
            "Micronaut": "heroku/java",
            "Quarkus": "heroku/java",

            # Go
            "Go Fiber": "heroku/go",
            "Gin": "heroku/go",
            "Echo": "heroku/go",

            # Ruby
            "Ruby on Rails": "heroku/ruby",
            "Sinatra": "heroku/ruby",

            # PHP
            "Laravel": "heroku/php",
            "Symfony": "heroku/php",

            # .NET
            ".NET": "heroku/dotnet",
            "ASP.NET Core": "heroku/dotnet",
        }

        # Try framework first
        if framework and framework in buildpack_map:
            return buildpack_map[framework]

        # Fallback to language
        language_buildpacks = {
            "Python": "heroku/python",
            "JavaScript": "heroku/nodejs",
            "TypeScript": "heroku/nodejs",
            "Java": "heroku/java",
            "Go": "heroku/go",
            "Ruby": "heroku/ruby",
            "PHP": "heroku/php",
            "C#": "heroku/dotnet"
        }

        if language and language in language_buildpacks:
            return language_buildpacks[language]

        # Default buildpack
        return "heroku/buildpacks:20"

    @staticmethod
    def get_github_token_from_jwt(request: Request) -> str:
        """Extract GitHub token from JWT cookie"""
        session_token = request.cookies.get("session")

        if not session_token:
            raise HTTPException(status_code=401, detail="Session token not found")

        try:
            payload = jwt.decode(session_token, JWT_SECRET, algorithms=["HS256"])
            github_token = payload.get("token")

            if not github_token:
                raise HTTPException(status_code=401, detail="Invalid token")

            return github_token
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    

       
    

