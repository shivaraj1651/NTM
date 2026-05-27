"""BrE spelling alias — re-exports everything from budget_optimizer.py.

Use either spelling; this module exists so imports using British English
spelling ('optimiser') work identically to 'optimizer'.
"""

from backend.app.agents.budget_optimizer import *  # noqa: F401, F403
from backend.app.agents.budget_optimizer import budget_optimizer_agent as budget_optimiser_agent  # noqa: F401
