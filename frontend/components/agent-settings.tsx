"use client";

import * as React from "react";
import {
  IconRobot,
  IconBrain,
  IconMessageCircle,
  IconCalendar,
  IconUsers,
  IconEdit,
  IconDeviceFloppy,
  IconX,
  IconPlayerPlay,
  IconCode,
  IconHistory,
  IconCopy,
  IconCheck,
} from "@tabler/icons-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface AgentConfig {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  status: "active" | "inactive" | "training";
  category: "qualification" | "outbound" | "scheduling" | "communication";
  currentPrompt: string;
  defaultPrompt: string;
  lastModified: string;
  performance: {
    successRate: number;
    avgResponseTime: string;
    totalProcessed: number;
  };
}

// Sample agent configurations
const defaultAgents: AgentConfig[] = [
  {
    id: "lead_qualifier",
    name: "Lead Qualifier",
    description: "Analyzes and scores incoming leads based on your criteria",
    icon: IconBrain,
    status: "active",
    category: "qualification",
    currentPrompt: `You are an expert lead qualification agent for PipeWise. Your role is to analyze incoming leads and determine their quality and potential value.

Analyze each lead based on:
1. Company size and industry relevance
2. Budget indicators and decision-making authority
3. Timeline and urgency signals
4. Engagement level and interest indicators

Provide a qualification score from 1-100 and categorize as:
- Hot (80-100): Ready to buy, high intent
- Warm (60-79): Interested, needs nurturing
- Cold (40-59): Low priority, long-term
- Unqualified (0-39): Not a good fit

Return your analysis in a structured format with reasoning.`,
    defaultPrompt: `You are an expert lead qualification agent for PipeWise. Your role is to analyze incoming leads and determine their quality and potential value.

Analyze each lead based on:
1. Company size and industry relevance
2. Budget indicators and decision-making authority
3. Timeline and urgency signals
4. Engagement level and interest indicators

Provide a qualification score from 1-100 and categorize as:
- Hot (80-100): Ready to buy, high intent
- Warm (60-79): Interested, needs nurturing
- Cold (40-59): Low priority, long-term
- Unqualified (0-39): Not a good fit

Return your analysis in a structured format with reasoning.`,
    lastModified: "2024-01-15",
    performance: {
      successRate: 87,
      avgResponseTime: "1.2s",
      totalProcessed: 1247,
    },
  },
  {
    id: "outbound_contact",
    name: "Outbound Contact",
    description: "Creates personalized outreach messages for qualified leads",
    icon: IconMessageCircle,
    status: "active",
    category: "outbound",
    currentPrompt: `You are a professional outbound sales agent for PipeWise. Create personalized, engaging outreach messages that convert leads into conversations.

For each qualified lead, craft a message that:
1. Addresses them by name and references their company
2. Demonstrates understanding of their business challenges
3. Clearly articulates how PipeWise solves their specific pain points
4. Includes a clear, compelling call-to-action
5. Maintains a professional yet conversational tone

Keep messages concise (150-200 words) and avoid being overly salesy. Focus on value and building rapport.

Tailor the approach based on lead category:
- Hot leads: Direct approach with meeting request
- Warm leads: Educational content + soft ask
- Cold leads: Value-first approach with no immediate ask`,
    defaultPrompt: `You are a professional outbound sales agent for PipeWise. Create personalized, engaging outreach messages that convert leads into conversations.

For each qualified lead, craft a message that:
1. Addresses them by name and references their company
2. Demonstrates understanding of their business challenges
3. Clearly articulates how PipeWise solves their specific pain points
4. Includes a clear, compelling call-to-action
5. Maintains a professional yet conversational tone

Keep messages concise (150-200 words) and avoid being overly salesy. Focus on value and building rapport.`,
    lastModified: "2024-01-12",
    performance: {
      successRate: 34,
      avgResponseTime: "2.1s",
      totalProcessed: 892,
    },
  },
  {
    id: "meeting_scheduler",
    name: "Meeting Scheduler",
    description: "Handles meeting coordination and calendar management",
    icon: IconCalendar,
    status: "active",
    category: "scheduling",
    currentPrompt: `You are a professional meeting scheduler for PipeWise. Your role is to coordinate meetings between prospects and sales team members efficiently.

When a prospect expresses interest in scheduling a meeting:
1. Offer 3-4 specific time slots within the next 3-5 business days
2. Confirm timezone and preferred meeting format (video call, phone, in-person)
3. Send calendar invitation with agenda and relevant materials
4. Include meeting preparation materials and company information
5. Follow up with confirmation and any pre-meeting questions

Be accommodating while maintaining professional boundaries. If scheduling conflicts arise, offer alternatives immediately.

Include these details in meeting invitations:
- Clear agenda and objectives
- Expected duration (typically 30-45 minutes)
- Video call link or location details
- Contact information for rescheduling
- Brief company overview and meeting preparation materials`,
    defaultPrompt: `You are a professional meeting scheduler for PipeWise. Your role is to coordinate meetings between prospects and sales team members efficiently.

When a prospect expresses interest in scheduling a meeting:
1. Offer 3-4 specific time slots within the next 3-5 business days
2. Confirm timezone and preferred meeting format
3. Send calendar invitation with agenda and relevant materials
4. Follow up with confirmation and any pre-meeting questions`,
    lastModified: "2024-01-10",
    performance: {
      successRate: 92,
      avgResponseTime: "0.8s",
      totalProcessed: 456,
    },
  },
  {
    id: "whatsapp_agent",
    name: "WhatsApp Agent",
    description: "Manages WhatsApp Business communications and lead engagement",
    icon: IconUsers,
    status: "active",
    category: "communication",
    currentPrompt: `You are a WhatsApp Business communication agent for PipeWise. Handle customer inquiries and lead engagement through WhatsApp with professionalism and efficiency.

Guidelines for WhatsApp interactions:
1. Respond promptly (within 5 minutes during business hours)
2. Use a friendly, conversational tone while remaining professional
3. Keep messages concise - WhatsApp users prefer short, clear responses
4. Use emojis sparingly and appropriately
5. Respect privacy and business communication standards

Response patterns:
- Greetings: Warm welcome with company introduction
- Inquiries: Answer questions directly, offer additional help
- Scheduling: Provide calendar links or coordinate timing
- Follow-ups: Professional check-ins without being pushy

Always capture lead information when appropriate and log interactions in the CRM system.`,
    defaultPrompt: `You are a WhatsApp Business communication agent for PipeWise. Handle customer inquiries and lead engagement through WhatsApp with professionalism and efficiency.

Guidelines for WhatsApp interactions:
1. Respond promptly and professionally
2. Keep messages concise and clear
3. Capture lead information when appropriate
4. Log all interactions in CRM system`,
    lastModified: "2024-01-08",
    performance: {
      successRate: 78,
      avgResponseTime: "0.5s",
      totalProcessed: 2341,
    },
  },
];

export function AgentSettings() {
  const [agents, setAgents] = React.useState<AgentConfig[]>(defaultAgents);
  const [editedPrompt, setEditedPrompt] = React.useState<string>("");
  const [saving, setSaving] = React.useState<Record<string, boolean>>({});
  const [testing, setTesting] = React.useState<Record<string, boolean>>({});
  const [copiedPrompts, setCopiedPrompts] = React.useState<Set<string>>(new Set());

  const handleEditPrompt = (agentId: string) => {
    const agent = agents.find((a) => a.id === agentId);
    if (agent) {
      setEditedPrompt(agent.currentPrompt);
    }
  };

  const handleSavePrompt = async (agentId: string) => {
    setSaving((prev) => ({ ...prev, [agentId]: true }));
    
    try {
      // TODO: Replace with actual API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      
      setAgents((prev) =>
        prev.map((agent) =>
          agent.id === agentId
            ? {
                ...agent,
                currentPrompt: editedPrompt,
                lastModified: new Date().toISOString().split('T')[0],
              }
            : agent
        )
      );
      
      setEditedPrompt("");
    } catch (error) {
      console.error("Error saving prompt:", error);
      alert("Failed to save prompt. Please try again.");
    } finally {
      setSaving((prev) => ({ ...prev, [agentId]: false }));
    }
  };

  const handleCancelEdit = () => {
    setEditedPrompt("");
  };

  const handleResetToDefault = (agentId: string) => {
    const agent = agents.find((a) => a.id === agentId);
    if (agent) {
      setEditedPrompt(agent.defaultPrompt);
    }
  };

  const handleTestPrompt = async (agentId: string) => {
    setTesting((prev) => ({ ...prev, [agentId]: true }));
    
    try {
      // TODO: Replace with actual API call to test prompt
      await new Promise((resolve) => setTimeout(resolve, 2000));
      alert("Prompt test completed successfully! Check the logs for detailed results.");
    } catch (error) {
      console.error("Error testing prompt:", error);
      alert("Failed to test prompt. Please try again.");
    } finally {
      setTesting((prev) => ({ ...prev, [agentId]: false }));
    }
  };

  const handleCopyPrompt = async (prompt: string, agentId: string) => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopiedPrompts((prev) => new Set([...prev, agentId]));
      setTimeout(() => {
        setCopiedPrompts((prev) => {
          const newSet = new Set(prev);
          newSet.delete(agentId);
          return newSet;
        });
      }, 2000);
    } catch (error) {
      console.error("Failed to copy prompt:", error);
    }
  };

  const getStatusColor = (status: AgentConfig["status"]) => {
    switch (status) {
      case "active":
        return "text-green-600 bg-green-100";
      case "inactive":
        return "text-gray-600 bg-gray-100";
      case "training":
        return "text-yellow-600 bg-yellow-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  const getCategoryColor = (category: AgentConfig["category"]) => {
    switch (category) {
      case "qualification":
        return "text-blue-600";
      case "outbound":
        return "text-purple-600";
      case "scheduling":
        return "text-green-600";
      case "communication":
        return "text-orange-600";
      default:
        return "text-gray-600";
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
          <IconRobot className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">
            AI Agent Configuration
          </h2>
          <p className="text-muted-foreground">
            Customize your AI agents with personalized prompts and behavior
          </p>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconRobot className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm font-medium">Total Agents</span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-bold">{agents.length}</span>
              <span className="text-muted-foreground text-sm ml-1">configured</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconCheck className="h-5 w-5 text-green-600" />
              <span className="text-sm font-medium">Active</span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-bold">
                {agents.filter((a) => a.status === "active").length}
              </span>
              <span className="text-muted-foreground text-sm ml-1">running</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconBrain className="h-5 w-5 text-blue-600" />
              <span className="text-sm font-medium">Avg Success Rate</span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-bold">
                {Math.round(
                  agents.reduce((acc, agent) => acc + agent.performance.successRate, 0) /
                  agents.length
                )}%
              </span>
              <span className="text-muted-foreground text-sm ml-1">accuracy</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconMessageCircle className="h-5 w-5 text-purple-600" />
              <span className="text-sm font-medium">Total Processed</span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-bold">
                {agents.reduce((acc, agent) => acc + agent.performance.totalProcessed, 0).toLocaleString()}
              </span>
              <span className="text-muted-foreground text-sm ml-1">leads</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Agents Configuration */}
      <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-2">
        {agents.map((agent) => {
          const Icon = agent.icon;
          const isSaving = saving[agent.id];
          const isTesting = testing[agent.id];
          const isCopied = copiedPrompts.has(agent.id);

          return (
            <Card key={agent.id} className="relative">
              <CardHeader className="space-y-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-lg ${getCategoryColor(
                        agent.category
                      )} bg-current/10`}
                    >
                      <Icon
                        className={`h-5 w-5 ${getCategoryColor(agent.category)}`}
                      />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{agent.name}</CardTitle>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge
                          variant="outline"
                          className={`text-xs ${getStatusColor(agent.status)}`}
                        >
                          {agent.status}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {agent.category}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
                <CardDescription className="text-sm leading-relaxed">
                  {agent.description}
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Performance Metrics */}
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-2xl font-bold text-green-600">
                      {agent.performance.successRate}%
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Success Rate
                    </div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold">
                      {agent.performance.avgResponseTime}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Avg Response
                    </div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold">
                      {agent.performance.totalProcessed.toLocaleString()}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Processed
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Prompt Preview */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-sm font-medium">Current Prompt</Label>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopyPrompt(agent.currentPrompt, agent.id)}
                      >
                        {isCopied ? (
                          <IconCheck className="h-4 w-4 text-green-600" />
                        ) : (
                          <IconCopy className="h-4 w-4" />
                        )}
                      </Button>
                      <span className="text-xs text-muted-foreground">
                        Modified: {agent.lastModified}
                      </span>
                    </div>
                  </div>
                  <div className="bg-muted/50 rounded-md p-3 text-sm max-h-32 overflow-y-auto">
                    {agent.currentPrompt.slice(0, 200)}...
                  </div>
                </div>
              </CardContent>

              <CardFooter className="flex gap-2">
                <Dialog>
                  <DialogTrigger asChild>
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={() => handleEditPrompt(agent.id)}
                    >
                      <IconEdit className="h-4 w-4 mr-2" />
                      Edit Prompt
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                      <DialogTitle className="flex items-center gap-2">
                        <Icon className={`h-5 w-5 ${getCategoryColor(agent.category)}`} />
                        Edit {agent.name} Prompt
                      </DialogTitle>
                      <DialogDescription>
                        Customize the behavior and responses of your {agent.name} agent.
                        Changes will be applied immediately after saving.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="prompt-editor" className="text-sm font-medium">
                          Agent Prompt
                        </Label>
                        <Textarea
                          id="prompt-editor"
                          placeholder="Enter your custom prompt here..."
                          value={editedPrompt}
                          onChange={(e) => setEditedPrompt(e.target.value)}
                          rows={15}
                          className="mt-2 font-mono text-sm"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Character count: {editedPrompt.length}
                        </p>
                      </div>
                    </div>
                    <DialogFooter className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() => handleResetToDefault(agent.id)}
                      >
                        <IconHistory className="h-4 w-4 mr-2" />
                        Reset to Default
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handleTestPrompt(agent.id)}
                        disabled={isTesting}
                      >
                        {isTesting ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
                            Testing...
                          </>
                        ) : (
                          <>
                            <IconPlayerPlay className="h-4 w-4 mr-2" />
                            Test Prompt
                          </>
                        )}
                      </Button>
                      <Button onClick={handleCancelEdit} variant="outline">
                        <IconX className="h-4 w-4 mr-2" />
                        Cancel
                      </Button>
                      <Button
                        onClick={() => handleSavePrompt(agent.id)}
                        disabled={isSaving || !editedPrompt.trim()}
                      >
                        {isSaving ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <IconDeviceFloppy className="h-4 w-4 mr-2" />
                            Save Changes
                          </>
                        )}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>

                <Button
                  variant="outline"
                  onClick={() => handleTestPrompt(agent.id)}
                  disabled={isTesting}
                >
                  {isTesting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <IconPlayerPlay className="h-4 w-4 mr-2" />
                      Test
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          );
        })}
      </div>

      {/* Help Section */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <IconCode className="h-5 w-5" />
            Prompt Engineering Tips
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h4 className="font-medium mb-2">Best Practices</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Be specific about the agent&apos;s role and objectives</li>
                <li>• Include clear instructions for different scenarios</li>
                <li>• Specify the desired output format</li>
                <li>• Test prompts thoroughly before deployment</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2">Variables Available</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• {`{lead_name}`} - Lead&apos;s full name</li>
                <li>• {`{company_name}`} - Company name</li>
                <li>• {`{lead_source}`} - Where the lead came from</li>
                <li>• {`{qualification_score}`} - Lead qualification score</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}