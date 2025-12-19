import httpx
import os
import json
from typing import Dict, Optional, Any


class NomadClient:
    """Client for interacting with Nomad API"""

    def __init__(self, nomad_addr: str = None):
        self.nomad_addr = nomad_addr or os.getenv("NOMAD_ADDR") or "http://127.0.0.1:4646"
        self.client = httpx.AsyncClient(timeout=120.0)

    async def submit_job(self, job_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a job to Nomad"""
        url = f"{self.nomad_addr}/v1/jobs"
        payload = {"Job": job_spec}

        print(f"Submitting job to Nomad: {job_spec.get('ID')}")
        print(f"Job spec: {json.dumps(payload, indent=2)}")

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Nomad API error: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
            raise

    async def submit_job_hcl(self, job_hcl: str, job_id: str) -> Dict[str, Any]:
        """Submit a job to Nomad using HCL format"""
        url = f"{self.nomad_addr}/v1/jobs/parse"

        print(f"Parsing HCL job: {job_id}")
        print(f"HCL content (first 500 chars):\n{job_hcl[:500]}")

        try:
            response = await self.client.post(
                url,
                json={"JobHCL": job_hcl, "Canonicalize": True}
            )
            response.raise_for_status()
            parsed_job = response.json()
            return await self.submit_job(parsed_job)
        except httpx.HTTPStatusError as e:
            print(f"Nomad HCL Parse error: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
            print(f"Full HCL:\n{job_hcl}")
            raise

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job information by ID"""
        url = f"{self.nomad_addr}/v1/job/{job_id}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def stop_job(self, job_id: str, purge: bool = False) -> Dict[str, Any]:
        """Stop a running job"""
        url = f"{self.nomad_addr}/v1/job/{job_id}"
        params = {"purge": str(purge).lower()}

        response = await self.client.delete(url, params=params)
        response.raise_for_status()

        return response.json()

    async def get_job_allocations(self, job_id: str) -> list[Dict[str, Any]]:
        """Get allocations for a job"""
        url = f"{self.nomad_addr}/v1/job/{job_id}/allocations"

        response = await self.client.get(url)
        response.raise_for_status()

        return response.json()

    async def get_allocation_logs(
        self, alloc_id: str, task: str, log_type: str = "stdout"
    ) -> str:
        """Get logs from an allocation"""
        url = f"{self.nomad_addr}/v1/client/fs/logs/{alloc_id}"

        params = {
            "task": task,
            "type": log_type,
            "plain": "true",
        }

        response = await self.client.get(url, params=params)
        response.raise_for_status()

        return response.text

    async def get_allocation_ports(self, alloc_id: str) -> Dict[str, int]:
        """Get mapped ports for an allocation"""
        url = f"{self.nomad_addr}/v1/allocation/{alloc_id}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            ports = {}
            if "Resources" in data and "Networks" in data["Resources"]:
                for network in data["Resources"]["Networks"]:
                    for port in network.get("DynamicPorts", []):
                        ports[port["Label"]] = port["Value"]
            return ports
        except Exception as e:
            print(f"Error getting allocation ports: {e}")
            return {}

    def generate_build_and_deploy_job_hcl(
        self,
        project_id: str,
        project_name: str,
        username: str,
        repo_name: str,
        image_name: str,
        branch: str = "main",
        secrets: list[dict] = None,
        start_command: str = None,
        cpu: int = 256,
        memory: int = 256,
        image_url: str = None,
        subdirectory: str = None,
        build_command: str = None,
        port: str = None,
        registry_url: str = None,
        registry_user: str = None,
        registry_password: str = None
    ) -> str:
        """
        Универсальный генератор HCL для любого проекта.
        - Builder: клонирует репозиторий через git, билдит через docker build, пушит через docker push
        - Server: запускает образ с динамическим портом Nomad в host режиме
        """

        secrets = secrets or []

        env_lines = [f'            {s["key"]} = "{s["value"]}"' for s in secrets]
        env_block = "\n".join(env_lines) if env_lines else ""

        # Use image_url if provided, otherwise construct from registry
        if image_url is None:
            # Use provided registry URL or default to localhost:5000
            reg_url = registry_url or "127.0.0.1:5000"
            # Remove protocol if present for docker tag
            reg_host = reg_url.replace("https://", "").replace("http://", "").rstrip("/")
            image_url = f"{reg_host}/{image_name}"

        # Extract registry host for docker login
        reg_host = registry_url.replace("https://", "").replace("http://", "").rstrip("/") if registry_url else "127.0.0.1:5000"
        
        # Auth block for server task (pulling image)
        auth_config = ""
        if registry_user and registry_password:
            auth_config = f"""
            auth {{
                username = "{registry_user}"
                password = "{registry_password}"
            }}
            """

        # Prepare build paths
        dockerfile_path = "Dockerfile"
        build_context = "."
        if subdirectory:
            dockerfile_path = f"{subdirectory}/Dockerfile"
            build_context = subdirectory

        # GitHub repo URL
        github_url = f"https://github.com/{username}/{repo_name}.git"
        
        # Build command for docker:cli
        # Escape special characters for shell
        escaped_password = registry_password.replace("'", "'\\''") if registry_password else ""
        
        build_script = f"""set -e
echo "🔐 Logging into registry {reg_host}..."
echo '{escaped_password}' | docker login {reg_host} -u {registry_user} --password-stdin

echo "📦 Installing git..."
apk add --no-cache git

echo "📥 Cloning repository {github_url}..."
git clone --branch {branch} --depth 1 {github_url} /build

echo "🏗️ Building Docker image..."
cd /build
docker build -t {image_url} -f {dockerfile_path} {build_context}

echo "🚀 Pushing image to registry..."
docker push {image_url}

echo "✅ Build complete!"
"""

        print(f"🐳 Generated build config:")
        print(f"   Image: {image_url}")
        print(f"   Registry: {reg_host}")
        print(f"   User: {registry_user if registry_user else 'NOT SET'}")
        print(f"   Password: {'***' if registry_password else 'NOT SET'}")

        return f"""
job "app-{project_id}" {{
    datacenters = ["dc1"]
    type = "service"

    group "app" {{
        count = 1

        network {{
            
            port "http" {{
                to = {port if port else "8080"}
            }}
        }}

        service {{
            name = "app-{project_id}"
            port = "http"
            tags = [
                "traefik.enable=true",
                "traefik.http.routers.app-{project_id}.rule=Host(`{project_name}.localhost`)",
                "traefik.http.routers.app-{project_id}.entrypoints=web"
            ]
        }}

        task "builder" {{
            driver = "docker"
            
            config {{
                image = "docker:cli"
                args = [
                    "sh",
                    "-c",
                    <<EOT
{build_script}
EOT
                ]
                volumes = [
                    "/var/run/docker.sock:/var/run/docker.sock"
                ]
                network_mode = "host"
            }}
            
            resources {{
                cpu    = 1000
                memory = 1024
            }}
            
            lifecycle {{
                hook = "prestart"
                sidecar = false
            }}
        }}
        
        task "server" {{
            driver = "docker"
            
            config {{
                network_mode = "host"
                ports = ["http"]
                image = "{image_url}"
                {auth_config}
                {f'''command = "sh"
                args = [
                    "-c",
                    <<EOF
{start_command}
EOF
                ]''' if start_command else ""}
            }} 
            
            
            env {{
{env_block}
                PORT = "{port if port else "8080"}"
            }}
            
            resources {{
                cpu    = {cpu}
                memory = {memory}
            }}
        }}
    }}
}}
"""

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Singleton instance
nomad_client = NomadClient()