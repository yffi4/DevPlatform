
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Optional, List
import asyncio
import json
import re

from nomad_client import nomad_client
from consul_client import consul_client
from deployment_kafka.kafka_producer import kafka_producer
from deployment_kafka.kafka_consumer import kafka_consumer
from dotenv import load_dotenv
import httpx
import os
import base64
import random

load_dotenv()

router = APIRouter()

# Secret Manager service URL
SECRET_MANAGER_URL = os.getenv("SECRET_MANAGER_URL")

# Nexus Configuration
NEXUS_URL = "http://127.0.0.1:5000"
NEXUS_USER = os.getenv("NEXUS_USER")
NEXUS_PASSWORD = os.getenv("NEXUS_PASSWORD")


class DeploymentConfig(BaseModel):
    """Configuration for deploying a user application"""
    repo_full_name: str  # e.g., "username/repo"
    app_name: str  # User-defined app name
    branch: str = "main"
    port: int = 8080
    domain: Optional[str] = None
    subdirectory: Optional[str] = None  # Subdirectory in repo containing Dockerfile (e.g., "frontend" or "backend/api")
    build_command: Optional[str] = None  # Custom build command
    env_vars: Optional[Dict[str, str]] = None
    cpu: int = 500
    memory: int = 512


def sanitize_app_name(username: str, app_name: str) -> str:
    """Create a unique, DNS-safe application name"""
    # Sanitize username
    safe_username = re.sub(r'[^a-z0-9-]', '-', username.lower())
    safe_username = re.sub(r'-+', '-', safe_username).strip('-')

    # Sanitize app name
    sanitized = re.sub(r'[^a-z0-9-]', '-', app_name.lower())
    sanitized = re.sub(r'-+', '-', sanitized).strip('-')

    return f"{safe_username}-{sanitized}"


async def get_secrets_from_vault(project_id: str) -> Dict[str, str]:
    """Get secrets for a project from Vault via secret-manager service"""
    try:
        # Sanitize project_id to match Vault storage format (/ -> _)
        safe_project_id = project_id.replace("/", "_")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SECRET_MANAGER_URL}/secrets/{safe_project_id}")

            if response.status_code == 404:
                # No secrets found for this project
                print(f"ℹ️  No secrets found in Vault for project: {project_id}")
                return {}

            response.raise_for_status()
            data = response.json()

            secrets = data.get("secrets", {})
            print(f"✓ Retrieved {len(secrets)} secrets from Vault for project: {project_id}")
            return secrets

    except httpx.HTTPError as e:
        print(f"⚠️  Failed to get secrets from Vault for {project_id}: {e}")
        return {}
    except Exception as e:
        print(f"⚠️  Error getting secrets from Vault: {e}")
        return {}


async def get_dockerfile_content(owner: str, repo: str, branch: str, token: str, path: str = None) -> str:
    """Fetch Dockerfile content from GitHub"""
    file_path = "Dockerfile"
    if path:
        file_path = f"{path.rstrip('/')}/Dockerfile"
    
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    params = {"ref": branch}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        
        if response.status_code == 404:
            return None
            
        response.raise_for_status()
        data = response.json()
        
        if "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8")
        return None


def parse_dockerfile_port(dockerfile_content: str) -> Optional[int]:
    """Parse EXPOSE instruction from Dockerfile content"""
    if not dockerfile_content:
        return None
        
    # Look for EXPOSE <port>
    # Handles "EXPOSE 8080" or "EXPOSE 80/tcp"
    matches = re.search(r'^\s*EXPOSE\s+(\d+)(?:/tcp|/udp)?', dockerfile_content, re.MULTILINE | re.IGNORECASE)
    
    if matches:
        return int(matches.group(1))
    
    return None


def get_user_id_from_jwt(request: Request) -> tuple[str, str, str]:
    """Extract user ID, username, and GitHub token from Kafka cache using access token from JWT"""
    import jwt
    import os

    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        JWT_SECRET = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET")
        payload = jwt.decode(session_token, JWT_SECRET, algorithms=["HS256"])
        access_token = payload.get("token")

        if not access_token:
            print(f"⚠️ No access token in JWT payload: {payload}")
            raise HTTPException(status_code=401, detail="Invalid token: no access token")

        # Get user info from Kafka cache
        user_info = kafka_consumer.get_user_info_by_token(access_token)
        user_id = user_info.get("user_id")
        username = user_info.get("username", "")

        if not user_id:
            print(f"⚠️ User not found in cache for token: {access_token[:20]}...")
            print(f"⚠️ Cache contains {len(kafka_consumer.user_cache)} users")
            raise HTTPException(status_code=401, detail="User not found in cache")

        print(f"✓ Found user: {username} (ID: {user_id}) for token")
        return user_id, username, access_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def deployment_stream(config: DeploymentConfig, user_id: str, username: str, github_token: str):
    """
    Stream deployment progress to the client using SSE
    
    Stages:
    1. Validating configuration
    2. Creating build job
    3. Building Docker image
    4. Pushing image to registry
    5. Creating deployment job
    6. Starting application
    7. Registering with Consul
    8. Configuring Traefik routing
    9. Deployment complete
    """
    
    async def send_event(stage: str, status: str, message: str, progress: int, data: dict = None):
        """Helper to send SSE event"""
        payload = {
            "stage": stage,
            "status": status,
            "message": message,
            "progress": progress
        }
        if data:
            payload.update(data)
        return f"data: {json.dumps(payload)}\n\n"
    
    try:
        # Stage 1: Validating
        yield await send_event("validating", "running", "Validating deployment configuration...", 10)
        await asyncio.sleep(0.5)

        app_name = sanitize_app_name(username, config.app_name)

        # Check if app already exists
        existing_job = await nomad_client.get_job(app_name)
        if existing_job:
            yield await send_event("validating", "error", f"Application '{app_name}' already exists. Please delete it first or use a different name.", 10)
            return

        # Get secrets from Vault
        yield await send_event("validating", "running", "Loading secrets from Vault...", 15)
        vault_secrets = await get_secrets_from_vault(config.repo_full_name)

        # Merge env vars from frontend with secrets from Vault (Vault takes precedence)
        env_vars = {**(config.env_vars or {}), **vault_secrets}

        yield await send_event("validating", "success", f"Configuration validated (loaded {len(vault_secrets)} secrets from Vault)", 20)
        
        # Analyze Dockerfile for port
        yield await send_event("validating", "running", "Analyzing Dockerfile...", 18)
        repo_parts = config.repo_full_name.split('/')
        detected_port = None
        
        if len(repo_parts) == 2:
            owner, repo = repo_parts
            try:
                dockerfile_content = await get_dockerfile_content(owner, repo, config.branch, github_token, config.subdirectory)
                
                if dockerfile_content:
                    detected_port = parse_dockerfile_port(dockerfile_content)
                    if detected_port:
                        config.port = detected_port
                        yield await send_event("validating", "info", f"Detected port {config.port} from Dockerfile", 18)
                    else:
                        yield await send_event("validating", "info", "No EXPOSE instruction found.", 18)
                else:
                    yield await send_event("validating", "warning", "Dockerfile not found.", 18)
            except Exception as e:
                print(f"Error fetching Dockerfile: {e}")
                yield await send_event("validating", "warning", f"Failed to analyze Dockerfile: {e}", 18)

        # Fallback to random dynamic port if no port detected (and default 8080 was passed)
        # If user explicitly set a non-default port in frontend (if capable), we might trust it?
        # But here config.port defaults to 8080. If detected_port is None, we override.
        if not detected_port:
             random_port = random.randint(20000, 30000)
             config.port = random_port
             yield await send_event("validating", "info", f"Assigned free dynamic port: {config.port}", 18)

        yield await send_event("validating", "info", f"Nexus config loaded: URL={os.getenv('NEXUS_URL')}, User={os.getenv('NEXUS_USER') if os.getenv('NEXUS_USER') else 'N/A'}, Password={'***' if os.getenv('NEXUS_PASSWORD') else 'N/A'}", 20)


        # Send Kafka event: deployment started
        await kafka_producer.send_deployment_started(
            app_name=app_name,
            repo_full_name=config.repo_full_name,
            user_id=user_id,
            framework=None  # Will be detected during build
        )

        # Stage 2: Creating build job
        yield await send_event("build_setup", "running", "Creating build job in Nomad...", 25)
        await asyncio.sleep(0.5)
        
        # Determine image name
        docker_image = f"{app_name}:latest"
        
        yield await send_event("build_setup", "success", f"Build job configured: {docker_image}", 30)
        
        # Stage 3: Building Docker image
        yield await send_event("building", "running", f"Building Docker image from GitHub: {config.repo_full_name}...", 35)

        # Extract repo name from full name (owner/repo -> repo)
        repo_name_only = config.repo_full_name.split('/')[-1] if '/' in config.repo_full_name else config.repo_full_name

        # Convert env_vars dict to secrets list format
        secrets_list = [{"key": k, "value": v} for k, v in env_vars.items()]

        # Create and submit build+deploy job
        build_job_hcl = nomad_client.generate_build_and_deploy_job_hcl(
            project_id=app_name,
            project_name=app_name,
            username=username,
            repo_name=repo_name_only,
            image_name=docker_image,
            registry_url=NEXUS_URL,
            registry_user=NEXUS_USER,
            registry_password=NEXUS_PASSWORD,
            port=str(config.port),
            branch=config.branch,
            secrets=secrets_list,
            cpu=config.cpu,
            memory=config.memory,
            subdirectory=config.subdirectory,
        )

        result = await nomad_client.submit_job_hcl(job_hcl=build_job_hcl, job_id=app_name)
        eval_id = result.get("EvalID")
        
        yield await send_event("building", "success", f"Build started (Evaluation ID: {eval_id})", 50)
        
        # Stage 4: Wait for build to complete
        yield await send_event("deploying", "running", "Waiting for build to complete and container to start...", 60)
        
        # Poll for allocations
        max_attempts = 120  # 120 * 2 seconds = 4 minutes (increased for build time)
        direct_url = None
        
        for attempt in range(max_attempts):
            await asyncio.sleep(2)
            
            allocations = await nomad_client.get_job_allocations(app_name)
            
            if allocations:
                # Check allocation status
                # Filter for the main app allocation (task group "app")
                alloc = allocations[0] # Simplification, should probably filter
                
                client_status = alloc.get("ClientStatus", "")
                
                if client_status == "running":
                    # Get dynamic port
                    alloc_id = alloc.get("ID")
                    node_name = alloc.get("NodeName", "localhost")
                    # In local setup, NodeName might not be resolvable, use localhost or node IP if known.
                    # Nomad often returns node details.
                    # For local dev, we assume the node is reachable at the same IP as Nomad client or localhost.
                    # Let's try to get the node ID or address from allocation if possible, but NomandClient.get_allocation_ports returns mapping.
                    
                    ports = await nomad_client.get_allocation_ports(alloc_id)
                    http_port = ports.get("http")
                    
                    # Construct direct URL
                    # Assuming local nomad node is accessible on localhost for the user since they said "fully local"
                    if http_port:
                        direct_url = f"http://localhost:{http_port}"
                    
                    yield await send_event("deploying", "success", "Application is running!", 70, {"direct_url": direct_url})
                    break
                elif client_status in ["failed", "lost"]:
                    # Get logs to show error
                    alloc_id = alloc.get("ID")
                    try:
                        logs = await nomad_client.get_allocation_logs(alloc_id, task="builder", log_type="stderr")
                        error_msg = logs[-500:] if len(logs) > 500 else logs  # Last 500 chars
                        yield await send_event("deploying", "error", f"Build failed: {error_msg}", 70)
                    except:
                        yield await send_event("deploying", "error", f"Build failed with status: {client_status}", 70)
                    return
                else:
                    # Still pending
                    progress = 60 + (attempt / max_attempts * 10)
                    yield await send_event("deploying", "running", f"Container status: {client_status}...", int(progress))
        
        # Stage 5: Registering with Consul
        yield await send_event("registering", "running", "Registering service with Consul...", 75)
        await asyncio.sleep(1)
        
        # Wait for service to appear in Consul
        max_consul_attempts = 30
        service_registered = False
        for attempt in range(max_consul_attempts):
            await asyncio.sleep(1)
            services = await consul_client.get_service(app_name)
            if services:
                service_registered = True
                break
        
        if not service_registered:
            yield await send_event("registering", "warning", "Service not yet registered in Consul (may take a moment)", 80)
        else:
            yield await send_event("registering", "success", "Service registered with Consul", 85)
        
        # Stage 6: Configuring routing
        yield await send_event("routing", "running", "Configuring Traefik routing...", 90)
        await asyncio.sleep(1)
        
        domain = config.domain or f"{app_name}.localhost"
        yield await send_event("routing", "success", f"Routing configured: http://{domain}", 95)

        # Stage 7: Complete
        msg = f"Deployment complete! App: http://{domain}"
        if direct_url:
            msg += f" | Direct: {direct_url}"
            
        yield await send_event("complete", "success", msg, 100, {
            "domain_url": f"http://{domain}",
            "direct_url": direct_url
        })

        # Send Kafka event: deployment completed
        await kafka_producer.send_deployment_completed(
            app_name=app_name,
            repo_full_name=config.repo_full_name,
            user_id=user_id,
            domain=domain,
            framework=None
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Deployment failed: {e}")
        yield await send_event("error", "error", f"Deployment failed: {str(e)}", 0)

        # Send Kafka event: deployment failed
        try:
            await kafka_producer.send_deployment_failed(
                app_name=app_name,
                repo_full_name=config.repo_full_name,
                user_id=user_id,
                error=str(e),
                framework=None
            )
        except:
            pass  # Don't fail if Kafka send fails


@router.post("/deploy")
async def deploy_application(config: DeploymentConfig, request: Request):
    """
    Deploy a user application with SSE progress streaming

    Returns a Server-Sent Events (SSE) stream with deployment progress
    """
    user_id, username, github_token = get_user_id_from_jwt(request)

    return StreamingResponse(
        deployment_stream(config, user_id, username, github_token),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/deployments")
async def list_deployments(request: Request):
    """List all deployments for the authenticated user"""
    user_id, username, _ = get_user_id_from_jwt(request)
    
    try:
        user_services = await consul_client.get_user_services(user_id)
        
        deployments = []
        for service in user_services:
            health = await consul_client.health_check(service["name"])
            healthy_count = sum(
                1 for h in health if h.get("Checks", [{}])[0].get("Status") == "passing"
            )
            
            domain = None
            for tag in service.get("tags", []):
                if tag.startswith("traefik.http.routers.") and ".rule=" in tag:
                    match = re.search(r'Host\(`([^`]+)`\)', tag)
                    if match:
                        domain = match.group(1)
                        break
            
            deployments.append({
                "app_name": service["name"],
                "domain": domain,
                "instances": len(service.get("instances", [])),
                "healthy_instances": healthy_count,
                "tags": service.get("tags", []),
            })
        
        return {
            "user_id": user_id,
            "deployments": deployments,
            "total": len(deployments),
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list deployments: {str(e)}"
        )


@router.get("/deployments/{app_name}")
async def get_deployment(app_name: str, request: Request):
    """Get detailed information about a specific deployment"""
    user_id, username, _ = get_user_id_from_jwt(request)

    # Check if app belongs to user (supports both old user{id}- and new {username}- formats)
    if not (app_name.startswith(f"user{user_id}-") or app_name.startswith(f"{username}-")):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        job = await nomad_client.get_job(app_name)
        if not job:
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        allocations = await nomad_client.get_job_allocations(app_name)
        service_instances = await consul_client.get_service(app_name)
        
        # Enhance allocations with port info
        enhanced_allocs = []
        for alloc in allocations:
             if alloc["ClientStatus"] == "running":
                  ports = await nomad_client.get_allocation_ports(alloc["ID"])
                  alloc["DynamicPorts"] = ports
                  # Assume localhost for local dev if NodeName ip is internal docker ip
                  if "http" in ports:
                       alloc["DirectUrl"] = f"http://localhost:{ports['http']}"
             enhanced_allocs.append(alloc)
        
        return {
            "app_name": app_name,
            "job": job,
            "allocations": enhanced_allocs,
            "service_instances": service_instances,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment: {str(e)}")


@router.delete("/deployments/{app_name}")
async def delete_deployment(app_name: str, request: Request, purge: bool = True):
    """Stop and remove a deployment"""
    user_id, username, _ = get_user_id_from_jwt(request)

    # Check if app belongs to user (supports both old user{id}- and new {username}- formats)
    if not (app_name.startswith(f"user{user_id}-") or app_name.startswith(f"{username}-")):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        result = await nomad_client.stop_job(app_name, purge=purge)
        
        return {
            "status": "deleted",
            "app_name": app_name,
            "message": "Deployment deleted successfully",
            "evaluation_id": result.get("EvalID"),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@router.get("/deployments/{app_name}/logs")
async def get_deployment_logs(app_name: str, request: Request, log_type: str = "stdout"):
    """Get logs from a deployment"""
    user_id, username, _ = get_user_id_from_jwt(request)

    # Check if app belongs to user (supports both old user{id}- and new {username}- formats)
    if not (app_name.startswith(f"user{user_id}-") or app_name.startswith(f"{username}-")):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        allocations = await nomad_client.get_job_allocations(app_name)
        
        if not allocations:
            raise HTTPException(status_code=404, detail="No running instances found")
        
        latest_alloc = max(allocations, key=lambda a: a.get("CreateTime", 0))
        alloc_id = latest_alloc["ID"]
        
        logs = await nomad_client.get_allocation_logs(alloc_id, task="app", log_type=log_type)
        
        return {
            "app_name": app_name,
            "allocation_id": alloc_id,
            "log_type": log_type,
            "logs": logs,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")
