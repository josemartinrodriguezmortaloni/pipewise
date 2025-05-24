from fastapi import FastAPI
from lead_workflow import LeadAPIHandler

app = FastAPI()
handler = LeadAPIHandler()


@app.post("/leads")
async def create_lead(lead_data: dict):
    return await handler.handle_post_leads(lead_data)
