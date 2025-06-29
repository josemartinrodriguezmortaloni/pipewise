import { openai } from "@ai-sdk/openai";
import { streamText, convertToCoreMessages, CoreMessage } from "ai";
import { z } from "zod";

// IMPORTANT! Set the runtime to edge
export const runtime = "edge";

// System message to define the AI's personality and capabilities
const systemMessage: CoreMessage = {
  role: "system",
  content: `You are a helpful and friendly PipeWise AI assistant.
  Your goal is to assist users with lead qualification, meeting scheduling, and other tasks by using the available tools.
  Be proactive, ask clarifying questions, and provide clear, concise answers.
  When a user provides lead information, use the 'analyze_lead' tool.
  When a user wants to schedule something, use the 'schedule_meeting' tool.
  You have access to the following tools:`,
};

export async function POST(req: Request) {
  // Check for OpenAI API key
  if (!process.env.OPENAI_API_KEY) {
    return new Response(
      "Missing OPENAI_API_KEY - make sure to set it in your .env.local file",
      {
        status: 500,
      }
    );
  }

  const { messages } = await req.json();

  // Add the system message to the beginning of the messages array
  const allMessages: CoreMessage[] = [
    systemMessage,
    ...convertToCoreMessages(messages),
  ];

  const result = await streamText({
    model: openai("gpt-4o"),
    messages: allMessages,
    tools: {
      analyze_lead: {
        description: "Analyze lead information and qualification status.",
        parameters: z.object({
          lead_info: z
            .string()
            .describe("The lead's information, e.g., name, company, title."),
        }),
      },
      schedule_meeting: {
        description: "Schedule a meeting with a lead.",
        parameters: z.object({
          lead_email: z.string().describe("The email of the lead to meet."),
          meeting_type: z
            .string()
            .describe(
              "The type of meeting to schedule, e.g., 'demo', 'intro call'."
            ),
        }),
      },
      send_email: {
        description: "Sends an email to a prospect.",
        parameters: z.object({
          recipient: z.string().describe("The email address of the recipient."),
          subject: z.string().describe("The subject of the email."),
          content: z.string().describe("The content of the email."),
        }),
      },
      twitter_dm: {
        description: "Sends a direct message on Twitter.",
        parameters: z.object({
          username: z.string().describe("The Twitter username to message."),
          message: z.string().describe("The content of the message."),
        }),
      },
    },
  });

  return result.toDataStreamResponse();
}
