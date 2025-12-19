from fastapi import APIRouter
from .schemas import SecretRequest, SecretResponse
import hvac
from fastapi import HTTPException
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")

# Initialize Vault clientf
vault_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)

@router.post("/secrets", response_model=SecretResponse)
async def store_secrets(request: SecretRequest):
    """
    Store secrets in Vault for a specific project

    Secrets are stored at path: secret/data/projects/{project_id}
    """
    try:
        # Validate Vault is available
        if vault_client.sys.is_sealed():
            raise HTTPException(
                status_code=503,
                detail="Vault is sealed and cannot accept requests"
            )

        # Sanitize project_id to be Vault-path-safe
        safe_project_id = request.project_id.replace("/", "_")
        secret_path = f"projects/{safe_project_id}"

        # Store secrets in Vault (KV v2)
        vault_client.secrets.kv.v2.create_or_update_secret(
            path=secret_path,
            secret=request.secrets,
            mount_point='secret'
        )

        return SecretResponse(
            status="success",
            message=f"Secrets stored successfully for project {request.project_id}",
            project_id=request.project_id,
            secrets_count=len(request.secrets)
        )

    except hvac.exceptions.VaultError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vault error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store secrets: {str(e)}"
        )


@router.get("/secrets/{project_id}")
async def get_secrets(project_id: str):
    """
    Retrieve secrets from Vault for a specific project

    Returns the secrets stored at: secret/data/projects/{project_id}
    """
    try:
        # Validate Vault is available
        if vault_client.sys.is_sealed():
            raise HTTPException(
                status_code=503,
                detail="Vault is sealed and cannot accept requests"
            )

        # Sanitize project_id
        safe_project_id = project_id.replace("/", "_")
        secret_path = f"projects/{safe_project_id}"

        # Read secrets from Vault (KV v2)
        secret_version = vault_client.secrets.kv.v2.read_secret_version(
            path=secret_path,
            mount_point='secret'
        )

        if not secret_version or 'data' not in secret_version:
            raise HTTPException(
                status_code=404,
                detail=f"No secrets found for project {project_id}"
            )

        return {
            "status": "success",
            "project_id": project_id,
            "secrets": secret_version['data']['data'],
            "version": secret_version['data']['metadata']['version']
        }

    except hvac.exceptions.InvalidPath:
        raise HTTPException(
            status_code=404,
            detail=f"No secrets found for project {project_id}"
        )
    except hvac.exceptions.VaultError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vault error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve secrets: {str(e)}"
        )


@router.delete("/secrets/{project_id}")
async def delete_secrets(project_id: str):
    """
    Delete secrets from Vault for a specific project
    """
    try:
        # Validate Vault is available
        if vault_client.sys.is_sealed():
            raise HTTPException(
                status_code=503,
                detail="Vault is sealed and cannot accept requests"
            )

        # Sanitize project_id
        safe_project_id = project_id.replace("/", "_")
        secret_path = f"projects/{safe_project_id}"

        # Delete secrets from Vault (KV v2) - this is a soft delete
        vault_client.secrets.kv.v2.delete_latest_version_of_secret(
            path=secret_path,
            mount_point='secret'
        )

        return {
            "status": "success",
            "message": f"Secrets deleted for project {project_id}",
            "project_id": project_id
        }

    except hvac.exceptions.InvalidPath:
        raise HTTPException(
            status_code=404,
            detail=f"No secrets found for project {project_id}"
        )
    except hvac.exceptions.VaultError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vault error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete secrets: {str(e)}"
        )