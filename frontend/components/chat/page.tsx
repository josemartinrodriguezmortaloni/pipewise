"use client";

import React, { useState, useRef, useEffect } from "react";
import { useChat } from "ai/react";
import { motion, AnimatePresence } from "framer-motion";
import { PromptBox } from "@/components/ui/prompt-box";
import {
  ChatBubble,
  ChatBubbleAvatar,
  ChatBubbleMessage,
  ChatBubbleAction,
  ChatBubbleActionWrapper,
} from "@/components/ui/chat-bubble";
import { TextShimmer } from "@/components/ui/text-shimmer";
import { AgentPlan } from "@/components/ui/agent-plan";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Copy, RefreshCcw, User, Bot, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AgentWorkflowData {
  workflowId: string;
  currentAgent: string;
  currentStep: string;
  tasks?: any[];
  progress?: number;
}

export default function ChatPageClient() {
  const [showWorkflow, setShowWorkflow] = useState(false);
  const [workflowData, setWorkflowData] = useState<AgentWorkflowData | null>(
    null
  );
  const [hasMessages, setHasMessages] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showPlan, setShowPlan] = useState(false);
  const [workflow, setWorkflow] = useState<AgentWorkflowData | null>(null);

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    data,
    setInput,
  } = useChat({
    api: "/api/chat",
    initialMessages: [],
    onResponse: (response) => {
      console.log("Chat response received:", response);
    },
    onFinish: (message) => {
      console.log("Chat message finished:", message);
      setHasMessages(true);

      // Check if message contains tool calls to show workflow
      if (
        message.content?.includes("agent") ||
        message.content?.includes("workflow")
      ) {
        setShowWorkflow(true);
        setWorkflowData({
          workflowId: Date.now().toString(),
          currentAgent: "AI Assistant",
          currentStep: "Processing request...",
          progress: 25,
        });
      }
    },
    onError: (err) => {
      console.error("Chat error:", err);
    },
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Custom submit handler for PromptBox
  const handlePromptSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      handleSubmit(e);
      setHasMessages(true);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const regenerateMessage = (messageIndex: number) => {
    // Logic to regenerate a specific message
    console.log("Regenerating message at index:", messageIndex);
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Main Chat Area */}
      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${
          showWorkflow ? "mr-80" : ""
        }`}
      >
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
                    Soy tu asistente de PipeWise. Puedo ayudarte con la
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
                      placeholder="Message..."
                    />
                  </form>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Messages List */}
          {hasMessages && messages.length > 0 && (
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
                        variant={message.role === "user" ? "sent" : "received"}
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
                            {message.content}
                          </ChatBubbleMessage>

                          {/* Agent response actions */}
                          {message.role === "assistant" && (
                            <ChatBubbleActionWrapper className="mt-2">
                              <ChatBubbleAction
                                icon={<Copy className="h-3 w-3" />}
                                onClick={() => copyToClipboard(message.content)}
                              />
                              <ChatBubbleAction
                                icon={<RefreshCcw className="h-3 w-3" />}
                                onClick={() => regenerateMessage(index)}
                              />
                            </ChatBubbleActionWrapper>
                          )}
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
                      <ChatBubbleAvatar fallback="AI" />
                      <div className="flex-1">
                        <ChatBubbleMessage isLoading />
                        <div className="mt-2">
                          <TextShimmer className="text-sm text-muted-foreground">
                            Procesando tu solicitud...
                          </TextShimmer>
                        </div>
                      </div>
                    </ChatBubble>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>
          )}

          {/* Error Display */}
          {error && (
            <div className="absolute bottom-20 left-4 right-4">
              <Card className="p-4 border-destructive bg-destructive/10">
                <p className="text-destructive text-sm">
                  Error: {error.message}
                </p>
              </Card>
            </div>
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
                  placeholder="Message..."
                />
              </form>
            </div>
          </motion.div>
        )}
      </div>

      {/* Workflow Sidebar */}
      <AnimatePresence>
        {showWorkflow && (
          <motion.div
            initial={{ x: 320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 320, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="fixed right-0 top-0 h-full w-80 bg-background border-l shadow-lg z-50"
          >
            <div className="p-4 border-b">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Agent Workflow</h3>
                <button
                  onClick={() => setShowWorkflow(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  ✕
                </button>
              </div>
              {workflowData && (
                <div className="mt-2 text-sm text-muted-foreground">
                  <p>Agent: {workflowData.currentAgent}</p>
                  <p>Status: {workflowData.currentStep}</p>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-hidden">
              <AgentPlan />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="fixed bottom-24 left-1/2 -translate-x-1/2 w-auto max-w-lg"
          >
            <div className="bg-destructive/10 border border-destructive/30 text-destructive p-4 rounded-lg flex items-center gap-3">
              <AlertTriangle className="h-5 w-5" />
              <div className="text-sm">
                <p className="font-bold">An error occurred</p>
                <p>{error.message}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
