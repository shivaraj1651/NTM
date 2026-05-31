"""Router aggregator — mounts all domain routers onto the FastAPI app."""

from fastapi import FastAPI

from backend.app.routers.mandate import router as mandate_router
from backend.app.routers.clients import router as clients_router
from backend.app.routers.campaign import router as campaign_router
from backend.app.routers.activations import router as activations_router
from backend.app.routers.creatives import router as creatives_router
from backend.app.routers.creative_director import router as creative_director_router
from backend.app.routers.digital_activator import router as digital_activator_router
from backend.app.routers.analytics import router as analytics_router
from backend.app.routers.replanning import router as replanning_router
from backend.app.routers.report import router as report_router
from backend.app.routers.admin import router as admin_router
from backend.app.routers.physical_activation import router as physical_activation_router
from backend.app.routers.auth_ext import router as auth_ext_router
from backend.app.routers.auth_session import router as auth_session_router


def register_routers(app: FastAPI) -> None:
    app.include_router(mandate_router)
    app.include_router(clients_router)
    app.include_router(campaign_router)
    app.include_router(activations_router)
    app.include_router(creatives_router)
    app.include_router(creative_director_router)
    app.include_router(digital_activator_router)
    app.include_router(analytics_router)
    app.include_router(replanning_router)
    app.include_router(report_router)
    app.include_router(admin_router)
    app.include_router(physical_activation_router)
    app.include_router(auth_ext_router)
    app.include_router(auth_session_router)
