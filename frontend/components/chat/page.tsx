"use client";

import React, { useState, useRef, useEffect } from "react";
import { useChat } from "@ai-sdk/react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AgentPlan } from "@/components/ui/agent-plan";
import { Badge } from "@/components/ui/badge";
import { MessageCircle, Bot, User, Loader2 } from "lucide-react";
import {
  ChatBubble,
  ChatBubbleAvatar,
  ChatBubbleMessage,
} from "@/components/ui/chat-bubble";
import { TextShimmer } from "@/components/ui/text-shimmer";
import { AlertTriangle, StopCircle } from "lucide-react";
import { toast } from "sonner";
import { PromptBox } from "@/components/ui/prompt-box";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface AgentWorkflowData {
  workflowId: string;
  currentAgent: string;
  currentStep: string;
  tasks?: any[];
  progress?: number;
  status?: string;
  metadata?: any;
  leadData?: any; // Added for dynamic task descriptions
}

// Error handling utilities
interface ErrorResponse {
  message: string;
  showToUser: boolean;
  recoverable: boolean;
  category: string;
}

function categorizeStreamError(error: any): string {
  if (!error) return "unknown";

  const message = error.message || error.toString();
  const stack = error.stack || "";

  // Enhanced error categorization for streaming errors
  if (
    message.includes("additionalProperties") ||
    message.includes("Pydantic")
  ) {
    return "pydantic_schema";
  }

  if (
    message.includes("fetch") ||
    message.includes("network") ||
    message.includes("ERR_NETWORK")
  ) {
    return "network";
  }

  if (message.includes("timeout") || message.includes("AbortError")) {
    return "timeout";
  }

  if (
    message.includes("Backend") ||
    message.includes("500") ||
    message.includes("503")
  ) {
    return "backend_unavailable";
  }

  if (
    message.includes("stream") ||
    message.includes("processDataStream") ||
    stack.includes("processDataStream")
  ) {
    return "stream_processing";
  }

  if (message.includes("onErrorPart") || stack.includes("onErrorPart")) {
    return "stream_processing";
  }

  if (
    message.includes("RLS") ||
    message.includes("security") ||
    message.includes("unauthorized")
  ) {
    return "database_security";
  }

  if (
    message.includes("tool") ||
    message.includes("function") ||
    stack.includes("tool")
  ) {
    return "tool_execution";
  }

  // Generic "An error occurred" usually means tool execution failed
  if (
    message.trim() === "An error occurred." ||
    message.includes("An error occurred")
  ) {
    return "tool_execution";
  }

  return "unknown";
}

function handleCategorizedError(category: string, error: any): ErrorResponse {
  const errorResponses: Record<string, ErrorResponse> = {
    tool_execution: {
      message:
        "Procesando tu solicitud. Los agentes están trabajando en segundo plano.",
      showToUser: false, // Don't show to user, let workflow continue
      recoverable: true,
      category,
    },
    stream_processing: {
      message: "Conectando con los agentes. Por favor espera un momento.",
      showToUser: false, // Don't interrupt the user experience
      recoverable: true,
      category,
    },
    pydantic_schema: {
      message: "Sistema actualizándose. Funcionalidad continuará normalmente.",
      showToUser: false,
      recoverable: true,
      category,
    },
    network: {
      message:
        "Problema de conexión. Verificando conectividad con el servidor.",
      showToUser: true,
      recoverable: true,
      category,
    },
    timeout: {
      message:
        "La solicitud está tomando más tiempo de lo esperado. Por favor espera.",
      showToUser: false, // Let it continue processing
      recoverable: true,
      category,
    },
    backend_unavailable: {
      message:
        "Servidor temporalmente no disponible. Usando modo de simulación.",
      showToUser: false,
      recoverable: true,
      category,
    },
    database_security: {
      message:
        "Configuración del sistema actualizándose. Funcionalidad básica disponible.",
      showToUser: false,
      recoverable: true,
      category,
    },
    authentication: {
      message: "Error de autenticación. Por favor inicia sesión de nuevo.",
      showToUser: true,
      recoverable: false,
      category,
    },
    unknown: {
      message:
        "Procesando solicitud. Si el problema persiste, intenta refrescar la página.",
      showToUser: false, // Don't interrupt workflow
      recoverable: true,
      category,
    },
  };

  return errorResponses[category] || errorResponses.unknown;
}

function trackErrorEvent(
  category: string,
  error: any,
  response: ErrorResponse
) {
  // Enhanced error tracking for debugging and monitoring
  const errorData = {
    category,
    message: error?.message || "Unknown error",
    userFacing: response.showToUser,
    recoverable: response.recoverable,
    timestamp: new Date().toISOString(),
    userAgent:
      typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
  };

  console.group(`🔍 Error Event: ${category}`);
  console.log("Error Details:", errorData);
  console.log("Response:", response);
  console.log("Stack:", error?.stack);
  console.groupEnd();

  // In production, this would send to a monitoring service
  if (process.env.NODE_ENV === "production") {
    // Example: analytics.track('stream_error', errorData);
  }
}

// Add markdown components configuration
const markdownComponents = {
  h1: ({ children }: any) => (
    <h1 className="text-2xl font-bold mb-4">{children}</h1>
  ),
  h2: ({ children }: any) => (
    <h2 className="text-xl font-semibold mb-3">{children}</h2>
  ),
  h3: ({ children }: any) => (
    <h3 className="text-lg font-semibold mb-2">{children}</h3>
  ),
  p: ({ children }: any) => <p className="mb-2">{children}</p>,
  ul: ({ children }: any) => (
    <ul className="list-disc pl-5 mb-2">{children}</ul>
  ),
  ol: ({ children }: any) => (
    <ol className="list-decimal pl-5 mb-2">{children}</ol>
  ),
  li: ({ children }: any) => <li className="mb-1">{children}</li>,
  code: ({ inline, children }: any) => {
    return inline ? (
      <code className="bg-muted px-1 py-0.5 rounded text-sm">{children}</code>
    ) : (
      <pre className="bg-muted p-3 rounded-md overflow-x-auto mb-2">
        <code>{children}</code>
      </pre>
    );
  },
  blockquote: ({ children }: any) => (
    <blockquote className="border-l-4 border-muted-foreground/30 pl-4 italic my-2">
      {children}
    </blockquote>
  ),
};

// Transform workflow data to AgentPlan tasks format
function transformWorkflowToTasks(workflowData: AgentWorkflowData) {
  const tasks = workflowData.tasks || [];

  // Add real-time agent information to tasks
  const transformedTasks = tasks.map((task: any, index: number) => {
    // Determine if this task is currently active based on workflow state
    const isCurrentTask =
      workflowData.currentStep === task.title ||
      workflowData.currentStep === task.name ||
      (workflowData.status === "in-progress" && task.status === "in-progress");

    return {
      id: task.id || String(Math.random()),
      title: task.title || task.name || "Task",
      description: task.description || getTaskDescription(task, workflowData),
      status: task.status || "pending",
      priority: task.priority || "medium",
      level: 0,
      dependencies: task.dependencies || [],
      subtasks: createAgentSpecificSubtasks(task, workflowData, isCurrentTask),
    };
  });

  // If no tasks exist, create default workflow tasks based on agent state
  if (transformedTasks.length === 0) {
    return createDefaultWorkflowTasks(workflowData);
  }

  return transformedTasks;
}

// Helper function to get dynamic task descriptions
function getTaskDescription(
  task: any,
  workflowData: AgentWorkflowData
): string {
  const currentAgent = workflowData.currentAgent || "AI Assistant";
  const leadData = workflowData.leadData || {};

  if (
    task.title?.includes("Lead Qualification") ||
    task.title?.includes("Qualification")
  ) {
    return `${currentAgent} está evaluando la información del lead y determinando la calidad de la oportunidad.`;
  }

  if (
    task.title?.includes("Twitter") ||
    task.title?.includes("Communication")
  ) {
    const username = leadData.twitter_username || leadData.name || "prospecto";
    return `${currentAgent} está preparando y enviando comunicación personalizada a @${username}.`;
  }

  if (task.title?.includes("Meeting") || task.title?.includes("Schedule")) {
    return `${currentAgent} está coordinando y programando reuniones con el prospecto calificado.`;
  }

  return task.description || `${currentAgent} está procesando esta tarea.`;
}

// Helper function to create agent-specific subtasks
function createAgentSpecificSubtasks(
  task: any,
  workflowData: AgentWorkflowData,
  isCurrentTask: boolean
) {
  const subtasks = task.subtasks || [];
  const currentAgent = workflowData.currentAgent || "AI Assistant";
  const progress = workflowData.progress || 0;

  // If this is the current task, add dynamic subtasks based on agent state
  if (isCurrentTask && subtasks.length === 0) {
    if (task.title?.includes("Lead Qualification")) {
      return [
        {
          id: `${task.id}-analyze`,
          title: "Analizar información del lead",
          description: `${currentAgent} está revisando los datos disponibles del prospecto`,
          status: progress > 25 ? "completed" : "in-progress",
          priority: "high",
          tools: ["crm-database", "lead-analyzer"],
        },
        {
          id: `${task.id}-score`,
          title: "Calcular puntuación de calificación",
          description:
            "Evaluando factores de calificación y asignando puntuación",
          status:
            progress > 50
              ? "completed"
              : progress > 25
              ? "in-progress"
              : "pending",
          priority: "high",
          tools: ["qualification-engine"],
        },
        {
          id: `${task.id}-update`,
          title: "Actualizar estado en CRM",
          description:
            "Guardando resultados de calificación en la base de datos",
          status:
            progress > 75
              ? "completed"
              : progress > 50
              ? "in-progress"
              : "pending",
          priority: "medium",
          tools: ["crm-database"],
        },
      ];
    }

    if (
      task.title?.includes("Twitter") ||
      task.title?.includes("Communication")
    ) {
      return [
        {
          id: `${task.id}-prepare`,
          title: "Preparar mensaje personalizado",
          description: "Creando mensaje adaptado al perfil del prospecto",
          status: progress > 33 ? "completed" : "in-progress",
          priority: "high",
          tools: ["message-generator", "personalization-engine"],
        },
        {
          id: `${task.id}-send`,
          title: "Enviar mensaje via X",
          description: "Enviando comunicación a través de la plataforma X",
          status:
            progress > 66
              ? "completed"
              : progress > 33
              ? "in-progress"
              : "pending",
          priority: "high",
          tools: ["twitter-api", "social-media-integration"],
        },
        {
          id: `${task.id}-track`,
          title: "Registrar actividad",
          description: "Guardando registro de la comunicación en el CRM",
          status:
            progress > 90
              ? "completed"
              : progress > 66
              ? "in-progress"
              : "pending",
          priority: "medium",
          tools: ["crm-database", "activity-tracker"],
        },
      ];
    }
  }

  return subtasks;
}

// Helper function to create default workflow tasks when none exist
function createDefaultWorkflowTasks(workflowData: AgentWorkflowData) {
  const currentAgent = workflowData.currentAgent || "AI Assistant";
  const currentStep = workflowData.currentStep || "Inicializando";
  const progress = workflowData.progress || 0;

  return [
    {
      id: "default-workflow",
      title: `${currentAgent} - ${currentStep}`,
      description: `El agente ${currentAgent} está trabajando en: ${currentStep}`,
      status: progress > 90 ? "completed" : "in-progress",
      priority: "high",
      level: 0,
      dependencies: [],
      subtasks: [
        {
          id: "current-step",
          title: currentStep,
          description: `Progreso actual: ${progress}%`,
          status: progress > 90 ? "completed" : "in-progress",
          priority: "high",
          tools: ["ai-agent", "workflow-engine"],
        },
      ],
    },
  ];
}

export default function ChatPageClient() {
  const [workflowData, setWorkflowData] = useState<AgentWorkflowData | null>(
    null
  );
  const [hasMessages, setHasMessages] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    stop,
    reload,
    setInput,
    setMessages,
  } = useChat({
    api: "/api/chat",
    initialMessages: [],
    keepLastMessageOnError: true,
    onResponse: (response) => {
      console.log("Chat response received:", response);
      if (response.ok) {
        setHasMessages(true);
      }
    },
    onFinish: (message) => {
      console.log("Chat message finished:", message);
      setHasMessages(true);
      setIsRetrying(false);

      // Extract workflow data from message if available
      try {
        // Look for workflow data in the message content
        const content = message.content || "";

        // Check if message contains workflow information
        if (content.includes("Workflow ID:") || content.includes("workflow")) {
          // Create workflow data based on message content
          const workflowId =
            extractWorkflowId(content) || `workflow-${Date.now()}`;
          const leadData = extractLeadData(content);

          setWorkflowData({
            workflowId,
            currentAgent: "PipeWise Coordinator",
            currentStep: "Procesamiento completo",
            progress: 100,
            status: "completed",
            leadData,
            tasks: createTasksFromMessage(content, leadData),
          });
        }
      } catch (error) {
        console.error("Error extracting workflow data:", error);
      }
    },
    onError: (err) => {
      console.error("Chat error:", err);
      setIsRetrying(false);

      // Enhanced error categorization and handling
      const errorCategory = categorizeStreamError(err);
      const errorResponse = handleCategorizedError(errorCategory, err);

      // Only show user-facing errors that require action
      if (errorResponse.showToUser) {
        toast.error(errorResponse.message);
      } else {
        // Log non-critical errors for debugging
        console.info("Non-critical error handled:", errorResponse.message);
      }

      // Track error for monitoring (in production would send to service)
      trackErrorEvent(errorCategory, err, errorResponse);
    },
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Enhanced submit handler with better error handling
  const handlePromptSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Submit triggered with input:", input);

    if (input.trim()) {
      setHasMessages(true);
      setIsRetrying(false);

      // Create initial workflow data when user sends a message
      if (
        input.toLowerCase().includes("contacta") ||
        input.toLowerCase().includes("@") ||
        input.toLowerCase().includes("twitter")
      ) {
        const leadUsername = extractTwitterUsername(input);
        setWorkflowData({
          workflowId: `workflow-${Date.now()}`,
          currentAgent: "PipeWise Coordinator",
          currentStep: "Iniciando contacto",
          progress: 10,
          status: "in-progress",
          leadData: { twitter_username: leadUsername },
          tasks: [
            {
              id: "1",
              title: "Contacto Inicial",
              description: `Contactando a @${leadUsername} en X (Twitter)`,
              status: "in-progress",
              priority: "high",
              level: 0,
              dependencies: [],
              subtasks: [],
            },
          ],
        });
      }

      try {
        handleSubmit(e);
      } catch (error) {
        console.error("Submit error:", error);
        toast.error("Error al enviar el mensaje");
      }
    }
  };

  // Handle Enter key to submit
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        setHasMessages(true);
        try {
          handleSubmit(e as any);
        } catch (error) {
          console.error("Submit error:", error);
          toast.error("Error al enviar el mensaje");
        }
      }
    }
  };

  // Retry function for failed messages
  const handleRetry = () => {
    setIsRetrying(true);
    try {
      reload();
    } catch (error) {
      console.error("Retry error:", error);
      setIsRetrying(false);
      toast.error("Error al reintentar");
    }
  };

  // Stop generation
  const handleStop = () => {
    stop();
    toast.info("Generación detenida");
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        toast.success("Copiado al portapapeles");
      })
      .catch(() => {
        toast.error("Error al copiar");
      });
  };

  const regenerateMessage = (messageIndex: number) => {
    const newMessages = messages.slice(0, messageIndex);
    setMessages(newMessages);
    handleRetry();
  };

  const isInputEmpty = !input.trim();
  const showError = error && !isLoading && !isRetrying;

  return (
    <div className="flex h-screen bg-background">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col py-16">
        {/* Messages Area */}
        <div className="flex-1 relative">
          {/* Welcome State - When no messages */}
          <AnimatePresence>
            {!hasMessages && messages.length === 0 && (
              <motion.div
                initial={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -50 }}
                transition={{ duration: 0.3 }}
                className="absolute inset-0 flex flex-col items-center justify-center p-4"
              >
                <div className="text-center mb-8">
                  <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="text-3xl font-bold text-foreground mb-4"
                  >
                    ¿Cómo puedo ayudarte?
                  </motion.h1>
                  <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="text-muted-foreground"
                  >
                    Soy tu asistente de PipeWise. Puedo ayudarte con
                    calificación de leads, programar reuniones y más.
                  </motion.p>
                </div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="w-full max-w-2xl"
                >
                  <form onSubmit={handlePromptSubmit}>
                    <PromptBox
                      value={input}
                      onChange={handleInputChange}
                      onKeyDown={handleKeyDown}
                      placeholder="Escribe tu mensaje aquí..."
                      disabled={isLoading}
                    />
                  </form>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Messages List */}
          {hasMessages && messages.length > 0 && (
            <div className="h-full max-w-4xl mx-auto">
              <ScrollArea className="h-full">
                <div className="p-4 pb-20">
                  <AnimatePresence initial={false}>
                    {messages.map((message, index) => (
                      <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.1 }}
                        className="mb-6"
                      >
                        <ChatBubble
                          variant={
                            message.role === "user" ? "sent" : "received"
                          }
                        >
                          <ChatBubbleAvatar
                            fallback={message.role === "user" ? "U" : "AI"}
                            src={
                              message.role === "user"
                                ? undefined
                                : "/placeholder.svg?height=32&width=32"
                            }
                          />
                          <div className="flex-1">
                            <ChatBubbleMessage
                              variant={
                                message.role === "user" ? "sent" : "received"
                              }
                            >
                              {message.role === "assistant" ? (
                                <>
                                  <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={markdownComponents}
                                  >
                                    {message.content || "..."}
                                  </ReactMarkdown>
                                  <div>
                                    {workflowData && (
                                      <div className="mt-4">
                                        <AgentPlan
                                          tasks={transformWorkflowToTasks(
                                            workflowData
                                          )}
                                          workflowInfo={{
                                            currentAgent:
                                              workflowData.currentAgent,
                                            currentStep:
                                              workflowData.currentStep,
                                            progress: workflowData.progress,
                                            status: workflowData.status,
                                            leadData: workflowData.leadData,
                                          }}
                                          className="w-full"
                                        />
                                      </div>
                                    )}
                                  </div>
                                </>
                              ) : (
                                message.content || "..."
                              )}
                            </ChatBubbleMessage>
                          </div>
                        </ChatBubble>
                      </motion.div>
                    ))}
                  </AnimatePresence>

                  {/* Loading indicator */}
                  {isLoading && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mb-6"
                    >
                      <ChatBubble variant="received">
                        <div className="mt-2 flex items-center gap-2">
                          <TextShimmer className="text-sm text-muted-foreground">
                            Procesando tu solicitud...
                          </TextShimmer>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleStop}
                            className="h-6"
                          >
                            <StopCircle className="h-3 w-3 mr-1" />
                            Detener
                          </Button>
                        </div>
                      </ChatBubble>
                    </motion.div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>
            </div>
          )}

          {/* Error Display */}
          {showError && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute bottom-20 left-4 right-4"
            >
              <Card className="p-4 border-destructive bg-destructive/10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-destructive" />
                    <p className="text-destructive text-sm">
                      Error: {error.message}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRetry}
                    disabled={isRetrying}
                    className="ml-2"
                  >
                    {isRetrying ? "Reintentando..." : "Reintentar"}
                  </Button>
                </div>
              </Card>
            </motion.div>
          )}
        </div>

        {/* Input Area - Fixed at bottom when messages exist */}
        {hasMessages && (
          <motion.div
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="p-4 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
          >
            <div className="max-w-4xl mx-auto">
              <form onSubmit={handlePromptSubmit}>
                <PromptBox
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder="Escribe tu mensaje aquí..."
                  disabled={isLoading}
                />
              </form>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
// Helper functions for extracting workflow data from messages
function extractWorkflowId(content: string): string | null {
  const match = content.match(/Workflow ID[:\s]+([a-f0-9-]+)/i);
  return match ? match[1] : null;
}

function extractTwitterUsername(text: string): string {
  const match = text.match(/@([a-zA-Z0-9_]+)/);
  return match ? match[1] : "usuario";
}

function extractLeadData(content: string): any {
  const leadData: any = {};

  // Extract Twitter username
  const twitterMatch = content.match(/@([a-zA-Z0-9_]+)/);
  if (twitterMatch) {
    leadData.twitter_username = twitterMatch[1];
  }

  // Extract email
  const emailMatch = content.match(/Email:\s*([^\s\n]+@[^\s\n]+)/);
  if (emailMatch) {
    leadData.email = emailMatch[1];
  }

  // Extract name
  const nameMatch = content.match(/Name[:\s]+([^\n,]+)/);
  if (nameMatch) {
    leadData.name = nameMatch[1].trim();
  }

  // Extract company
  const companyMatch = content.match(/Company[:\s]+([^\n,]+)/);
  if (companyMatch) {
    leadData.company = companyMatch[1].trim();
  }

  return leadData;
}

function createTasksFromMessage(content: string, leadData: any) {
  const tasks = [];

  // Analyze content to determine what tasks were performed
  if (content.includes("Lead created") || content.includes("Lead Data")) {
    tasks.push({
      id: "lead-creation",
      title: "Creación de Lead",
      description: "Lead creado exitosamente en la base de datos",
      status: "completed",
      priority: "high",
      level: 0,
      dependencies: [],
      subtasks: [
        {
          id: "lead-validate",
          title: "Validar información",
          description: "Validación de datos del prospecto",
          status: "completed",
          priority: "high",
          tools: ["data-validator"],
        },
        {
          id: "lead-save",
          title: "Guardar en CRM",
          description: "Almacenamiento en base de datos",
          status: "completed",
          priority: "high",
          tools: ["crm-database"],
        },
      ],
    });
  }

  if (content.includes("Qualification") || content.includes("qualified")) {
    tasks.push({
      id: "lead-qualification",
      title: "Calificación de Lead",
      description: "Evaluación y calificación del prospecto",
      status: "completed",
      priority: "high",
      level: 0,
      dependencies: [],
      subtasks: [
        {
          id: "analyze-info",
          title: "Análisis de información",
          description: "Revisión de datos disponibles",
          status: "completed",
          priority: "high",
          tools: ["lead-analyzer"],
        },
        {
          id: "calculate-score",
          title: "Cálculo de puntuación",
          description: "Asignación de score de calificación",
          status: "completed",
          priority: "medium",
          tools: ["qualification-engine"],
        },
      ],
    });
  }

  if (
    content.includes("Outreach") ||
    content.includes("message") ||
    content.includes("contacted")
  ) {
    tasks.push({
      id: "outreach",
      title: "Comunicación con Prospecto",
      description: `Contacto realizado con ${
        leadData.twitter_username
          ? "@" + leadData.twitter_username
          : "el prospecto"
      }`,
      status: "completed",
      priority: "high",
      level: 0,
      dependencies: [],
      subtasks: [
        {
          id: "prepare-message",
          title: "Preparar mensaje",
          description: "Creación de mensaje personalizado",
          status: "completed",
          priority: "high",
          tools: ["message-generator"],
        },
        {
          id: "send-contact",
          title: "Enviar comunicación",
          description: "Envío de mensaje al prospecto",
          status: "completed",
          priority: "high",
          tools: ["communication-channel"],
        },
      ],
    });
  }

  // If no specific tasks found, create a general processing task
  if (tasks.length === 0) {
    tasks.push({
      id: "general-processing",
      title: "Procesamiento General",
      description: "Workflow completado exitosamente",
      status: "completed",
      priority: "medium",
      level: 0,
      dependencies: [],
      subtasks: [],
    });
  }

  return tasks;
}
