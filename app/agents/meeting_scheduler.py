import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROMPT_FILE_PATH = os.path.join(
    os.path.dirname(__file__), "prompts", "meetingSchedulerPrompt.md"
)
CALENDLY_ACCESS_TOKEN = os.environ.get("CALENDLY_ACCESS_TOKEN")


def load_prompt_from_file(file_path: str) -> str:
    """Loads content from a specified file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Handle the case where the prompt file is not found
        # You might want to log an error or raise a more specific exception
        print(f"Error: Prompt file not found at {file_path}")
        return (
            "Default prompt: Please configure the prompt file."  # Or raise an exception
        )
    except Exception as e:
        print(f"Error loading prompt file {file_path}: {e}")
        return "Error loading prompt."  # Or raise


class MeetingSchedulerAgent:
    model = "gpt-4.1"
    instuctions = load_prompt_from_file(PROMPT_FILE_PATH)
    client = OpenAI()

    def __init__(self, model, instructions, client):
        self.model = model
        self.instuctions = instructions
        self.client = client

    def meetingschedulerAgent(self, input: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=input,
            tools={
                "mcpServers": {
                    "calendly": {
                        "command": "python",
                        "args": ["./tools/calendly.py"],
                        "env": {"CALENDLY_ACCESS_TOKEN": CALENDLY_ACCESS_TOKEN},
                    }
                }
            },
        )
        return response.output_text

    def run(self, input: str) -> str:
        agent = self.meetingschedulerAgent(input)
        return agent
