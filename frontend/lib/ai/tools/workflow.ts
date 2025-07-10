import { tool } from "ai";
import { z } from "zod";

// Schema para los pasos del workflow
export const workflowStepSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  status: z.enum([
    "pending",
    "in-progress",
    "completed",
    "failed",
    "need-help",
  ]),
  priority: z.enum(["low", "medium", "high"]),
  tools: z.array(z.string()).optional(),
});

// Schema para el estado completo del workflow
export const workflowStateSchema = z.object({
  workflowId: z.string(),
  currentAgent: z.string(),
  currentStep: z.string(),
  progress: z.number().min(0).max(100),
  status: z.enum([
    "pending",
    "in-progress",
    "completed",
    "failed",
    "need-help",
  ]),
  tasks: z.array(workflowStepSchema),
  metadata: z.record(z.any()).optional(),
});

// Tool para inicializar workflow
export const startWorkflow = tool({
  description: "Initialize a new workflow and notify the frontend",
  parameters: z.object({
    workflowId: z.string(),
    agentName: z.string(),
    leadId: z.string(),
    initialTasks: z.array(workflowStepSchema),
    leadData: z
      .object({
        email: z.string().optional(),
        name: z.string().optional(),
        company: z.string().optional(),
        phone: z.string().optional(),
        message: z.string().optional(),
        twitter_username: z.string().optional(),
        instagram_username: z.string().optional(),
      })
      .optional(),
  }),
  execute: async (params) => {
    console.log("🚀 Starting workflow:", params);

    let backendSuccess = false;
    let backendError = null;
    let backendResult = null;
    let agentResponse = null;

    // Detect if this is a contact request (mentions @username)
    const isContactRequest =
      params.leadData?.twitter_username ||
      (params.leadId && params.leadId.includes("@")) ||
      params.initialTasks.some(
        (task) =>
          task.description.toLowerCase().includes("contact") ||
          task.description.toLowerCase().includes("twitter") ||
          task.description.toLowerCase().includes("@")
      );

    if (isContactRequest) {
      console.log(
        "🎯 Contact request detected - calling Python backend directly"
      );

      try {
        // Prepare data for backend API call
        const leadData = {
          workflow_type: "single_lead",
          email: params.leadData?.email || `${params.leadId}@example.com`,
          name: params.leadData?.name || params.leadId,
          company: params.leadData?.company || "",
          phone: params.leadData?.phone || "",
          message: params.leadData?.message || "",
          force_real_workflow: true,
          debug_mode: true,
        };

        console.log("📤 Calling Python backend directly:", leadData);

        // Call the Python backend API directly
        const backendUrl =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
        const response = await fetch(
          `${backendUrl}/api/process-lead-workflow`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(leadData),
          }
        );

        if (response.ok) {
          backendResult = await response.json();
          backendSuccess = true;
          console.log("✅ Backend processing completed:", backendResult);

          // Extract the agent response for the AI model to use
          if (backendResult.data && backendResult.data.result) {
            agentResponse = backendResult.data.result;
            console.log("🤖 Agent response extracted:", agentResponse);
          }
        } else {
          const errorText = await response.text();
          backendError = `HTTP ${response.status}: ${errorText}`;
          console.error("❌ Backend API error:", backendError);
        }
      } catch (error) {
        backendError = error instanceof Error ? error.message : String(error);
        console.error("⚠️ Backend connection failed:", backendError);
      }
    }

    // Return workflow status (this triggers the frontend workflow visualization)
    const result = {
      success: true,
      workflowId: params.workflowId,
      agentName: params.agentName,
      leadId: params.leadId,
      initialTasks: params.initialTasks,
      leadData: params.leadData,
      backendProcessing: {
        attempted: isContactRequest,
        success: backendSuccess,
        error: backendError,
        result: backendResult,
      },
      // Include agent response for the AI model to process
      agentResponse: agentResponse,
    };

    console.log("📊 Workflow started successfully:", result);

    // Return a result that includes the agent response for the AI model
    if (agentResponse) {
      return `Workflow started successfully. Agent processing result:

${agentResponse}

Workflow details: ${JSON.stringify({
        workflowId: params.workflowId,
        agentName: params.agentName,
        leadId: params.leadId,
        status: "completed",
        backendSuccess: backendSuccess,
      })}`;
    }

    // If no agent response, return standard workflow info
    return JSON.stringify(result);
  },
});

// Tool para actualizar workflow
export const updateWorkflow = tool({
  description: "Update workflow progress and status for real-time UI updates",
  parameters: workflowStateSchema,
  execute: async (params) => {
    console.log("🔄 Workflow update:", params);

    return {
      type: "workflow_update",
      ...params,
      timestamp: new Date().toISOString(),
    };
  },
});

// Tool para completar workflow
export const completeWorkflow = tool({
  description: "Mark workflow as completed and provide final results",
  parameters: z.object({
    workflowId: z.string(),
    finalResults: z.record(z.any()).optional().default({}),
    completedTasks: z.array(workflowStepSchema),
  }),
  execute: async (params) => {
    console.log("✅ Workflow completed:", params);

    const finalResults = params.finalResults || {};

    return {
      type: "workflow_complete",
      workflowId: params.workflowId,
      currentAgent: "Workflow Complete",
      currentStep: "All tasks completed successfully",
      progress: 100,
      status: "completed" as const,
      tasks: params.completedTasks,
      metadata: {
        ...finalResults,
        completedAt: new Date().toISOString(),
      },
    };
  },
});

// Tool para solicitar información al usuario
export const requestUserInformation = tool({
  description:
    "Request specific information from the user when more data is needed",
  parameters: z.object({
    question: z.string().describe("The specific question to ask the user"),
    informationNeeded: z
      .string()
      .describe("What type of information is needed"),
    context: z
      .string()
      .optional()
      .describe("Additional context about why this information is needed"),
    priority: z.enum(["low", "normal", "high", "urgent"]).default("normal"),
  }),
  execute: async (params) => {
    console.log("🔔 Requesting information from user:", params);

    return {
      type: "user_information_request",
      question: params.question,
      informationNeeded: params.informationNeeded,
      context: params.context,
      priority: params.priority,
      timestamp: new Date().toISOString(),
      status: "pending_user_response",
      // This will trigger a special UI component in the frontend
      uiComponent: "InformationRequestForm",
    };
  },
});

// Tool para solicitar decisión al usuario
export const requestUserDecision = tool({
  description: "Escalate a decision to the user when human input is needed",
  parameters: z.object({
    decisionNeeded: z
      .string()
      .describe("Description of the decision that needs to be made"),
    options: z
      .string()
      .describe("Available options (comma-separated or formatted list)"),
    recommendation: z
      .string()
      .optional()
      .describe("AI's recommendation with reasoning"),
    impact: z.string().optional().describe("Potential impact of the decision"),
  }),
  execute: async (params) => {
    console.log("⚡ Escalating decision to user:", params);

    return {
      type: "user_decision_request",
      decisionNeeded: params.decisionNeeded,
      options: params.options,
      recommendation: params.recommendation,
      impact: params.impact,
      timestamp: new Date().toISOString(),
      status: "pending_user_decision",
      // This will trigger a special UI component in the frontend
      uiComponent: "DecisionRequestForm",
    };
  },
});

export const workflowTools = {
  startWorkflow,
  updateWorkflow,
  completeWorkflow,
  requestUserInformation,
  requestUserDecision,
};
