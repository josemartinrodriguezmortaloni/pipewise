from fastapi import FastAPI
from lead_workflow import LeadAPIHandler
from app.agents.agent import Agents

app = FastAPI()
handler = LeadAPIHandler()


@app.post("/leads")
async def create_lead(lead_data: dict):
    agents = Agents()
    # ✅ Workflow completamente automatizado
    result = await agents.run_workflow(lead_data)
    return result
