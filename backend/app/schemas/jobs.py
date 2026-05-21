from typing import Literal
from pydantic import BaseModel


class JobQueuedResponse(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"
    campaign_id: str
