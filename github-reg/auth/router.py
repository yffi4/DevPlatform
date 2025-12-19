from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import httpx, os, time, jwt
from dotenv import load_dotenv
from kafka_reg import producer
from .schemas import DeployRequest

load_dotenv()

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_EXPIRATION = 60 * 15  


@router.get("/github/login")
async def github_login():
    """Redirect user to GitHub OAuth"""
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={os.getenv('CLIENT_ID')}"
        f"&redirect_uri={os.getenv('REDIRECTED_URI')}"
    )
    return RedirectResponse(github_auth_url)


@router.get("/github/callback")
async def github_callback(code: str):
    """Handle GitHub callback, fetch repos, and send to Kafka securely"""


    data = {
        "client_id": os.getenv('CLIENT_ID'),
        "client_secret": os.getenv('CLIENT_SECRET'),
        "code": code,
        "redirect_uri": os.getenv('REDIRECTED_URI'),
    }
    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        token_resp = await client.post("https://github.com/login/oauth/access_token", headers=headers, data=data)
    token_json = token_resp.json()
    access_token = token_json.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub token exchange failed")


    async with httpx.AsyncClient(timeout=20.0) as client:
        gh_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "fastapi-app",
        }
        gh_response = await client.get("https://api.github.com/user", headers=gh_headers)
        gh_response.raise_for_status()
        user_data = gh_response.json()


    await producer.kafka_produser.send_event("user_registered", {
        "user": {
            "id": user_data.get("id"),
            "login": user_data.get("login"),
            "github_token": access_token,
            

        }
        
    })


    payload = {
        "sub": "github_user",
        "token": access_token,
        "exp": int(time.time()) + JWT_EXPIRATION,
    }
    jwt_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

 
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    redirect_response = RedirectResponse(url=f"{frontend_url}/dashboard", status_code=302)

  
    redirect_response.set_cookie(
        key="session",
        value=jwt_token,
        httponly=True,
        secure=False,  
        samesite="lax",
        max_age=JWT_EXPIRATION,
        path="/",
        domain="localhost"  
    )

    return redirect_response


@router.get("/github/repos")
async def get_github_repos(request: Request):
    """Fetch user's GitHub repositories using JWT token from cookie"""

    # Get JWT token from cookie
    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Decode and validate JWT
    try:
        payload = jwt.decode(session_token, JWT_SECRET, algorithms=["HS256"])
        access_token = payload.get("token")

        if not access_token:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch repositories from GitHub
    async with httpx.AsyncClient(timeout=20.0) as client:
        gh_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "fastapi-app",
        }

        
        user_response = await client.get("https://api.github.com/user", headers=gh_headers)
        user_response.raise_for_status()
        user_data = user_response.json()

        #
        repos_response = await client.get("https://api.github.com/user/repos", headers=gh_headers)
        repos_response.raise_for_status()
        repos_data = repos_response.json()

        await producer.kafka_produser.send_event("repos_resp", {
            "repos": repos_data
        })

    return {
        "user": user_data,
        "repos": repos_data
    }





@router.get("/github/repo/{owner}/{repo}/contents")
async def get_repo_contents(owner: str, repo: str, request: Request, path: str = ""):
    """Get repository contents (files and folders) at a specific path"""

    # Get JWT token from cookie
    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Decode and validate JWT
    try:
        payload = jwt.decode(session_token, JWT_SECRET, algorithms=["HS256"])
        access_token = payload.get("token")

        if not access_token:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch repository contents from GitHub
    async with httpx.AsyncClient(timeout=20.0) as client:
        gh_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "fastapi-app",
        }

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        contents_response = await client.get(url, headers=gh_headers)
        contents_response.raise_for_status()
        contents_data = contents_response.json()

    return {
        "path": path,
        "contents": contents_data
    }


# @router.post("/github/deploy")
# async def deploy_repository(deploy_request: DeployRequest, request: Request):
#     """Send selected repository and folder to Kafka for deployment"""

#     session_token = request.cookies.get("session")
#     if not session_token:
#         raise HTTPException(status_code=401, detail="Not authenticated")

#     try:
#         payload = jwt.decode(session_token, JWT_SECRET, algorithms=["HS256"])
#         access_token = payload.get("token")

#         if not access_token:
#             raise HTTPException(status_code=401, detail="Invalid token")
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token expired")
#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")

#     async with httpx.AsyncClient(timeout=20.0) as client:
#         gh_headers = {
#             "Authorization": f"Bearer {access_token}",
#             "Accept": "application/vnd.github+json",
#             "X-GitHub-Api-Version": "2022-11-28",
#             "User-Agent": "fastapi-app",
#         }

#         user_response = await client.get("https://api.github.com/user", headers=gh_headers)
#         user_response.raise_for_status()
#         user_data = user_response.json()

#     await producer.kafka_produser.send_event("choose_settings_requested", {
#         "user": {
#             "id": user_data.get("id"),
#             "login": user_data.get("login"),
#         },
#         "repository": {
#             "owner": deploy_request.owner,
#             "name": deploy_request.repo,
#             "full_name": f"{deploy_request.owner}/{deploy_request.repo}",
#             "folder_path": deploy_request.folder_path,
#         },
#         "github_token": access_token,
#     })

#     return {
#         "status": "success",
#         "message": "Deployment request sent to queue",
#         "repository": f"{deploy_request.owner}/{deploy_request.repo}",
#         "folder_path": deploy_request.folder_path or "/"
#     }
