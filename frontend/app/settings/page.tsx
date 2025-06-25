"use client";

import { useState } from "react";
import { IntegrationsSettings } from "@/components/integrations-settings";
import { AgentSettings } from "@/components/agent-settings";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  IconSettings,
  IconPlug,
  IconRobot,
  IconShield,
  IconBell,
} from "@tabler/icons-react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("integrations");

  return (
    <div className="p-6 pr-6 pb-0">
      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
          <CardDescription>
            Configure your account, integrations, and AI agents
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="space-y-6"
          >
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger
                value="integrations"
                className="flex items-center gap-2"
              >
                <IconPlug className="h-4 w-4" />
                Integrations
              </TabsTrigger>
              <TabsTrigger value="agents" className="flex items-center gap-2">
                <IconRobot className="h-4 w-4" />
                AI Agents
              </TabsTrigger>
              <TabsTrigger value="security" className="flex items-center gap-2">
                <IconShield className="h-4 w-4" />
                Security
              </TabsTrigger>
              <TabsTrigger
                value="notifications"
                className="flex items-center gap-2"
              >
                <IconBell className="h-4 w-4" />
                Notifications
              </TabsTrigger>
              <TabsTrigger value="general" className="flex items-center gap-2">
                <IconSettings className="h-4 w-4" />
                General
              </TabsTrigger>
            </TabsList>

            <TabsContent value="integrations" className="space-y-6">
              <IntegrationsSettings />
            </TabsContent>

            <TabsContent value="agents" className="space-y-6">
              <AgentSettings />
            </TabsContent>

            <TabsContent value="security" className="space-y-6">
              <div className="text-center py-8">
                <h3 className="text-lg font-medium mb-2">Security Settings</h3>
                <p className="text-muted-foreground">
                  Coming soon - manage your security preferences and 2FA
                </p>
              </div>
            </TabsContent>

            <TabsContent value="notifications" className="space-y-6">
              <div className="text-center py-8">
                <h3 className="text-lg font-medium mb-2">
                  Notification Settings
                </h3>
                <p className="text-muted-foreground">
                  Coming soon - configure your notification preferences
                </p>
              </div>
            </TabsContent>

            <TabsContent value="general" className="space-y-6">
              <div className="text-center py-8">
                <h3 className="text-lg font-medium mb-2">General Settings</h3>
                <p className="text-muted-foreground">
                  Coming soon - configure general application settings
                </p>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
