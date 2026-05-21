"""Router aggregator — mounts all domain routers onto the FastAPI app."""

from fastapi import FastAPI

from backend.app.routers.mandate import router as mandate_router
from backend.app.routers.campaign import router as campaign_router
from backend.app.routers.creative_director import router as creative_director_router
from backend.app.routers.digital_activator import router as digital_activator_router
from backend.app.routers.analytics import router as analytics_router
from backend.app.routers.replanning import router as replanning_router
from backend.app.routers.report import router as report_router


def register_routers(app: FastAPI) -> None:
    app.include_router(mandate_router)
    app.include_router(campaign_router)
    app.include_router(creative_director_router)
    app.include_router(digital_activator_router)
    app.include_router(analytics_router)
    app.include_router(replanning_router)
    app.include_router(report_router)
