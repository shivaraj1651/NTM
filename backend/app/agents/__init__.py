"""
Agents module for NTM.

Agents are long-running AI-powered processes that analyze, validate, and
generate strategic content. Each agent has a single responsibility and
produces structured JSON output.
"""

from backend.app.agents import creative_director
from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.agents.audio_generator import AudioGeneratorAgent
from backend.app.agents.budget_optimizer import budget_optimizer_agent
from backend.app.agents.campaign_strategist import campaign_strategist_agent
from backend.app.agents.competitive_intel import competitive_intel_agent
from backend.app.agents.copywriter import CopywriterAgent
from backend.app.agents.creative_director_orchestrator import (
    CreativeDirectorAgent,
    creative_director_agent,
)
from backend.app.agents.digital_activator import DigitalActivatorAgent
from backend.app.agents.image_generator import ImageGeneratorAgent
from backend.app.agents.mandate_analyst import (
    MandateValidator,
    analyze_mandate_with_llm,
    mandate_analyst_agent,
)
from backend.app.agents.media_planner import media_planner_agent
from backend.app.agents.replanning_agent import ReplanningAgent
from backend.app.agents.report_generator import ReportAgent
from backend.app.agents.scriptwriter import ScriptwriterAgent
from backend.app.agents.video_generator import VideoGeneratorAgent

__all__ = [
    "MandateValidator",
    "analyze_mandate_with_llm",
    "mandate_analyst_agent",
    "creative_director",
    "CreativeDirectorAgent",
    "creative_director_agent",
    "competitive_intel_agent",
    "campaign_strategist_agent",
    "media_planner_agent",
    "budget_optimizer_agent",
    "CopywriterAgent",
    "ScriptwriterAgent",
    "ImageGeneratorAgent",
    "AudioGeneratorAgent",
    "VideoGeneratorAgent",
    "DigitalActivatorAgent",
    "AnalyticsAgent",
    "ReplanningAgent",
    "ReportAgent",
]
