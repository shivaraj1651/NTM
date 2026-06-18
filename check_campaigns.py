import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['ntm']
    campaigns = await db.campaigns.find({}).to_list(20)
    for c in campaigns:
        cid = c["_id"]
        status = c.get("status")
        tenant = c.get("tenant_id")
        concepts = len(c.get("concepts", []))
        print(f"id={cid}  status={status}  tenant={tenant}  concepts={concepts}")
    print(f"Total: {len(campaigns)}")

asyncio.run(main())
