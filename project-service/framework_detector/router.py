from fastapi import APIRouter, Request, HTTPException
from .framework_detector import FrameworkDetector
from .shemas import DeploymentRequest, DetectFrameworkRequest, FrameworkDetectionResponse, FrameworkListResponse
from project_kafka.kafka_producer import kafka_producer

router = APIRouter()


@router.get("/frameworks", response_model=FrameworkListResponse)
async def get_supported_frameworks():
    """
    Get list of all supported frameworks

    This endpoint returns all frameworks that can be detected or manually selected
    """
    return FrameworkListResponse(frameworks=FrameworkDetector.SUPPORTED_FRAMEWORKS)


@router.post("/detect-framework", response_model=FrameworkDetectionResponse)
async def detect_framework(request: Request, body: DetectFrameworkRequest):
    """
    Detect framework for a GitHub repository

    This endpoint:
    1. Analyzes the repository structure
    2. Detects the framework(s) used
    3. Sends an event to Kafka for CI/CD pipeline setup
    """
    github_token = FrameworkDetector.get_github_token_from_jwt(request)

    try:
        # Create detector instance
        detector = FrameworkDetector(github_token)

        # Detect framework
        result = await detector.detect_framework(body.repo_full_name, body.folder_path or "")

        # Send event to Kafka
        await kafka_producer.send_framework_detected(result)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Framework detection failed: {str(e)}")


@router.post("/deploy")
async def request_deployment(request: Request, body: DeploymentRequest):
    """
    Request deployment for a repository

    This endpoint:
    1. Detects the framework (or uses manually selected one)
    2. Sends deployment request to CI/CD pipeline service via Kafka with secrets
    """
    github_token = FrameworkDetector.get_github_token_from_jwt(request)

    try:
        # Create detector instance
        detector = FrameworkDetector(github_token)

        # Use manually selected framework or auto-detect
        if body.framework:
            # Validate that framework is supported
            if body.framework not in FrameworkDetector.SUPPORTED_FRAMEWORKS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Framework '{body.framework}' is not supported"
                )

            # Use manually selected framework
            framework_data = await detector.detect_framework(body.repo_full_name, body.folder_path or "")
            framework_data["primary_framework"] = body.framework
            # Update buildpack based on manual selection
            framework_data["buildpack"] = detector._get_buildpack(body.framework, framework_data.get("language"))
        else:
            # Auto-detect framework
            framework_data = await detector.detect_framework(body.repo_full_name, body.folder_path or "")

        if not framework_data.get("primary_framework"):
            raise HTTPException(
                status_code=400,
                detail="Could not detect framework for this repository. Please select a framework manually."
            )

        # Send deployment request to Kafka
        await kafka_producer.send_deployment_request(
            repo_full_name=body.repo_full_name,
            framework_data=framework_data,
            user_id=body.user_id
        )

        return {
            "status": "deployment_requested",
            "repo": body.repo_full_name,
            "folder_path": body.folder_path or "",
            "framework": framework_data.get("primary_framework"),
            "secrets_count": len(body.secrets) if body.secrets else 0,
            "message": "Deployment request sent to CI/CD pipeline"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment request failed: {str(e)}")