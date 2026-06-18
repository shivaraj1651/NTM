import asyncio
import os
os.environ["NTM_STUB_EXTERNAL"] = "1"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://ntm_user:ntm_pass@localhost:5432/ntm_db"
os.environ["MONGODB_URL"] = "mongodb://localhost:27017/ntm"

from backend.app.tasks.campaign_tasks import run_concept_generation

campaign_id = "18c0a40e-8dee-4d3a-8bc7-0f60dde0f538"
tenant_id = "fbeecfa7-f851-4b35-9c8e-d199ed10caae"

print("Running concept generation directly...")
try:
    result = run_concept_generation(campaign_id, tenant_id)
    print("Result:", result)
except Exception as e:
    import traceback
    traceback.print_exc()
