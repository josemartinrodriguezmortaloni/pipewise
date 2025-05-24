from app.agents.meeting_scheduler import MeetingSchedulerAgent

agent = MeetingSchedulerAgent()
result = await agent.run(
    {"lead": {"id": "test-123", "name": "Test User", "company": "Test Corp"}}
)
print("RESULTADO:", result)
