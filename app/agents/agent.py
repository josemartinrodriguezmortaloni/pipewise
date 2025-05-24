from dotenv import load_dotenv
from lead_qualifier import LeadAgent
from meeting_scheduler import MeetingSchedulerAgent
from outbound_contact import OutboundAgent

load_dotenv()


class Agents:
    def __init__(self) -> None:
        self.leadQualifier = LeadAgent
        self.OutBound = OutboundAgent
        self.meetScheduler = MeetingSchedulerAgent

    def runWorkflow(self, input: str) -> str:
        leadQualified = self.leadQualifier.run(input)
        OutBound = self.OutBound.run(leadQualified)
        MeetingScheduler = self.meetScheduler.run(OutBound)
        return MeetingScheduler
