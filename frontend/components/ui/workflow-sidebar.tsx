"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, CircleDotDashed, Circle, Clock } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface WorkflowStep {
  id: string;
  title: string;
  description: string;
  status: "pending" | "in-progress" | "completed";
  progress?: number;
  timestamp?: string;
}

interface WorkflowSidebarProps {
  workflowId?: string;
  currentAgent?: string;
  currentStep?: string;
  progress?: number;
  status?: string;
  steps?: WorkflowStep[];
  className?: string;
}

const defaultSteps: WorkflowStep[] = [
  {
    id: "init",
    title: "Workflow Started",
    description: "Initializing PipeWise AI Assistant for lead processing...",
    status: "completed",
    progress: 100,
  },
  {
    id: "processing",
    title: "Processing Lead Data",
    description: "Analyzing lead information and extracting insights",
    status: "completed",
    progress: 100,
  },
  {
    id: "contacting",
    title: "Contacting Executive Team",
    description: "Reaching out to decision makers",
    status: "completed",
    progress: 100,
  },
  {
    id: "crm",
    title: "Creating Leads in CRM",
    description: "Storing lead information in database",
    status: "completed",
    progress: 100,
  },
  {
    id: "strategy",
    title: "Coordinating Multi-touchpoint Strategy",
    description: "Planning comprehensive outreach approach",
    status: "completed",
    progress: 100,
  },
  {
    id: "scheduling",
    title: "Scheduling Meetings",
    description: "Coordinating meetings with decision makers",
    status: "completed",
    progress: 100,
  },
];

export function WorkflowSidebar({
  workflowId,
  currentAgent,
  currentStep,
  progress,
  status,
  steps = defaultSteps,
  className,
}: WorkflowSidebarProps) {
  return (
    <div className={`h-full flex flex-col bg-background ${className}`}>
      {/* Header */}
      <div className="p-4 border-b">
        <h3 className="font-semibold text-foreground">Agent Workflow</h3>
        {workflowId && (
          <p className="text-xs text-muted-foreground mt-1">
            ID: {workflowId.substring(0, 12)}...
          </p>
        )}
        {currentAgent && (
          <div className="mt-2 text-sm">
            <p className="text-muted-foreground">
              Current Agent:{" "}
              <span className="text-foreground font-medium">
                {currentAgent}
              </span>
            </p>
            {currentStep && (
              <p className="text-muted-foreground">
                Status: <span className="text-foreground">{currentStep}</span>
              </p>
            )}
          </div>
        )}
      </div>

      {/* Progress Overview */}
      {progress !== undefined && (
        <div className="p-4 border-b">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium">Overall Progress</span>
            <span className="text-sm text-muted-foreground">{progress}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      )}

      {/* Workflow Steps */}
      <div className="flex-1 overflow-auto p-4">
        <div className="space-y-3">
          <AnimatePresence>
            {steps.map((step, index) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="relative"
              >
                <Card
                  className={`p-4 border transition-all duration-200 ${
                    step.status === "completed"
                      ? "bg-green-50 border-green-200"
                      : step.status === "in-progress"
                      ? "bg-blue-50 border-blue-200"
                      : "bg-gray-50 border-gray-200"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Status Icon */}
                    <div className="flex-shrink-0 mt-1">
                      {step.status === "completed" ? (
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      ) : step.status === "in-progress" ? (
                        <CircleDotDashed className="h-5 w-5 text-blue-500 animate-pulse" />
                      ) : (
                        <Circle className="h-5 w-5 text-gray-400" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <h4
                        className={`font-medium text-sm ${
                          step.status === "completed"
                            ? "text-green-900"
                            : step.status === "in-progress"
                            ? "text-blue-900"
                            : "text-gray-700"
                        }`}
                      >
                        {step.title}
                      </h4>

                      <p
                        className={`text-xs mt-1 ${
                          step.status === "completed"
                            ? "text-green-700"
                            : step.status === "in-progress"
                            ? "text-blue-700"
                            : "text-gray-600"
                        }`}
                      >
                        {step.description}
                      </p>

                      {/* Step Progress */}
                      {step.progress !== undefined &&
                        step.status === "in-progress" && (
                          <div className="mt-2">
                            <div className="flex justify-between items-center mb-1">
                              <span className="text-xs text-muted-foreground">
                                Progress:
                              </span>
                              <span className="text-xs font-medium">
                                {step.progress}%
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-1.5">
                              <motion.div
                                className="h-1.5 rounded-full transition-all duration-300 bg-blue-500"
                                initial={{ width: 0 }}
                                animate={{ width: `${step.progress}%` }}
                                transition={{
                                  duration: 0.5,
                                  delay: index * 0.1,
                                }}
                              />
                            </div>
                          </div>
                        )}

                      {/* Timestamp */}
                      {step.timestamp && (
                        <div className="flex items-center gap-1 mt-2">
                          <Clock className="h-3 w-3 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">
                            {step.timestamp}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>

                {/* Connection Line */}
                {index < steps.length - 1 && (
                  <div className="absolute left-6 top-full w-px h-3 bg-gray-200 -translate-x-1/2" />
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Status Footer */}
        {status === "completed" && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-6"
          >
            <Card className="p-4 bg-green-50 border-green-200">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                <div>
                  <h4 className="font-medium text-green-900">
                    Workflow Completed
                  </h4>
                  <p className="text-sm text-green-700">
                    All tasks completed successfully!
                  </p>
                </div>
              </div>
            </Card>
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default WorkflowSidebar;
