import { openai } from "@ai-sdk/openai";
import { streamText } from "ai";
import { workflowTools } from "@/lib/ai/tools/workflow";

const SYSTEM_PROMPT = `You are PipeWise AI Assistant, a communication interface between users and the orchestrator system.

Your primary role is to:
1. Receive user requests and transmit them to the orchestrator
2. Display all orchestrator activities and progress to the user in real-time
3. Ask users for any information the orchestrator needs to complete tasks
4. Present orchestrator results in a clear, user-friendly format

**Core Functions:**
- Relay user instructions to the orchestrator system
- Show live updates of what the orchestrator is doing
- Request additional information when the orchestrator needs it
- Present orchestrator outputs in an understandable way

**Communication Flow:**
1. User makes a request → You transmit it to the orchestrator
2. Orchestrator works → You show the user what's happening
3. Orchestrator needs info → You ask the user for it
4. Orchestrator completes → You present the results clearly

**When using workflow tools:**
1. Use startWorkflow to begin orchestrator tasks
2. Use updateWorkflow to show orchestrator progress to the user
3. Use completeWorkflow when orchestrator finishes
4. Always keep the user informed about what the orchestrator is doing

**Information Requests:**
When the orchestrator needs additional data, ask the user clearly:
- What specific information is needed
- Why the orchestrator needs it
- How it will be used in the process

You are the bridge between the user and the orchestrator - transmit requests, display actions, and facilitate communication.`;

// Backend configuration
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export async function POST(request: Request) {
  try {
    const { messages, leadData, directProcessing } = await request.json();

    console.log("🔧 Unified API Request:", {
      hasMessages: !!messages,
      hasLeadData: !!leadData,
      directProcessing,
    });

    // Check if this is a direct lead processing request (not a chat conversation)
    if (directProcessing && leadData) {
      console.log(
        "📤 Direct lead processing mode is deprecated - redirecting to orchestrator"
      );

      // The frontend should not process leads directly
      // All requests should go through the orchestrator via chat conversation
      return new Response(
        JSON.stringify({
          error: "direct_processing_deprecated",
          message:
            "Direct lead processing is no longer supported. Please use the chat interface to communicate with the orchestrator.",
          suggestion:
            "Send your request through the chat and the orchestrator will handle all processing.",
          success: false,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Standard chat conversation mode
    console.log("💬 Chat conversation mode activated");
    console.log("Incoming Messages:", messages);

    const result = await streamText({
      model: openai("gpt-4.1"),
      system: SYSTEM_PROMPT,
      messages,
      maxSteps: 5,
      tools: workflowTools,
      temperature: 0,
      toolChoice: "auto",
      experimental_continueSteps: true, // Continue on tool errors
      onStepFinish: (step) => {
        console.log("Step finished:", step.stepType, step.text);

        // Log step completion for debugging
        if (step.stepType === "tool-result") {
          console.log("Tool completed successfully");
        }
      },
      onFinish: (completion) => {
        console.log("Completion finished:", completion.finishReason);
      },
    });

    return result.toDataStreamResponse({
      // Add custom headers for better error tracking
      headers: {
        "X-Stream-Version": "v2",
        "X-Error-Recovery": "enabled",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "X-Content-Type-Options": "nosniff",
      },
      // Enhanced data stream processing
      getErrorMessage: (error) => {
        console.error("Stream processing error:", error);

        // Return a simple string message for the stream
        return "Processing your request... Please wait.";
      },
    });
  } catch (error) {
    console.error("Chat API Error:", error);

    // Categorize error types for better handling
    const errorType = categorizeError(error);
    const errorSuggestions = getErrorSuggestions(errorType);

    // Return a structured error response that doesn't break the frontend
    return new Response(
      JSON.stringify({
        error: "api_error",
        errorType,
        message:
          "I encountered an issue processing your request. Let me try a different approach.",
        details: error instanceof Error ? error.message : "Unknown error",
        recoverable: true,
        timestamp: new Date().toISOString(),
        suggestions: errorSuggestions,
        fallback: {
          response:
            "I'm experiencing some technical difficulties. You can still interact with me, and I'll do my best to help.",
          action: "continue",
        },
      }),
      {
        status: 200, // Use 200 to prevent frontend from breaking
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-cache",
          "X-Error-Type": errorType,
          "X-Fallback-Mode": "enabled",
        },
      }
    );
  }
}

// Helper function to categorize errors
function categorizeError(error: any): string {
  if (!error) return "unknown";

  const message = error.message || error.toString();

  if (message.includes("additionalProperties")) return "pydantic_schema";
  if (message.includes("network") || message.includes("fetch"))
    return "network";
  if (message.includes("timeout")) return "timeout";
  if (message.includes("Backend")) return "backend_unavailable";
  if (message.includes("RLS") || message.includes("security"))
    return "database_security";
  if (message.includes("stream")) return "stream_processing";

  return "unknown";
}

// Helper function to provide error suggestions
function getErrorSuggestions(errorType: string): string[] {
  const suggestions: Record<string, string[]> = {
    pydantic_schema: [
      "Backend is updating schema configuration",
      "Workflow will continue with basic functionality",
    ],
    network: ["Check internet connection", "Refresh the page"],
    timeout: [
      "Request is taking longer than expected",
      "Please wait or try again",
    ],
    backend_unavailable: [
      "Backend is temporarily unavailable",
      "Using simulation mode",
    ],
    database_security: [
      "Database security policies are updating",
      "Core functionality continues",
    ],
    stream_processing: [
      "Stream processing issue",
      "Workflow continues with limited features",
    ],
    unknown: ["An unexpected error occurred", "Please try again"],
  };

  return suggestions[errorType] || suggestions.unknown;
}
