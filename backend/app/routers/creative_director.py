"""FastAPI router for Creative Director Agent (AGT-06) endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.agents.creative_director.models import (
    CampaignInput,
    CreativeDirectorOutput,
)
from backend.app.agents.creative_director_orchestrator import (
    CreativeDirectorAgent,
    creative_director_agent,
)
from backend.app.core.dependencies import require_role
from backend.app.core.models import User, UserRole

router = APIRouter(
    prefix="/api/agents/creative-director",
    tags=["creative-director"],
    responses={
        400: {"description": "Invalid input"},
        500: {"description": "Generation error"},
    }
)

CREATIVE_DIR_ROLES = [
    UserRole.CREATIVE_LEAD,
    UserRole.BRAND_MANAGER,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str


@router.post(
    "/generate",
    response_model=CreativeDirectorOutput,
    summary="Generate platform-specific marketing creatives",
    description="Generates creative content variations for specified platforms",
    responses={
        200: {"description": "Creatives generated successfully"},
        400: {"description": "Invalid campaign input"},
        500: {"description": "Generation failed"},
    }
)
async def generate_creatives(
    campaign_input: CampaignInput,
    _: User = Depends(require_role(CREATIVE_DIR_ROLES)),
) -> CreativeDirectorOutput:
    """Generate platform-specific marketing creatives.

    Orchestrates the full creative generation pipeline:
    1. Input validation and aggregation
    2. Core concept generation
    3. Platform-specific creative variations
    4. Validation and refinement
    5. Output compilation

    Args:
        campaign_input: Campaign context and requirements

    Returns:
        CreativeDirectorOutput with generated creatives and metadata

    Raises:
        HTTPException: 400 for validation errors, 500 for generation errors
    """
    try:
        # Validate input
        if not campaign_input.campaign_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="campaign_id is required"
            )

        if not campaign_input.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tenant_id is required"
            )

        if not campaign_input.platforms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one platform is required"
            )

        if campaign_input.brand_guidelines is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="brand_guidelines are required"
            )

        # Call agent
        output = await creative_director_agent(campaign_input)

        # Check if generation failed completely
        if output.metadata.validation_status == "failed" and not output.platforms:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=output.metadata.validation_summary or "Creative generation failed",
            )

        return output

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Creative generation failed: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the Creative Director Agent is operational",
    responses={
        200: {"description": "Service is healthy"},
    }
)
async def health_check(
    _: User = Depends(require_role(CREATIVE_DIR_ROLES)),
) -> HealthResponse:
    """Health check endpoint for Creative Director Agent.

    Returns:
        HealthResponse with status and message

    Raises:
        HTTPException: 500 if service is unhealthy
    """
    try:
        # Quick validation - can instantiate agent
        agent = CreativeDirectorAgent(api_key="temp")
        assert agent.generator is not None
        assert agent.validator is not None

        return HealthResponse(
            status="healthy",
            message="Creative Director Agent is operational"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service unhealthy: {str(e)}"
        )
