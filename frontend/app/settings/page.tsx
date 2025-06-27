"use client";

import { useState } from "react";
import { IntegrationsSettings } from "@/components/integrations-settings";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { IconPlug, IconBell } from "@tabler/icons-react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("integrations");

  // Notification settings state
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(true);
  const [leadNotifications, setLeadNotifications] = useState(true);
  const [meetingReminders, setMeetingReminders] = useState(true);
  const [systemUpdates, setSystemUpdates] = useState(false);
  const [notificationFrequency, setNotificationFrequency] =
    useState("realtime");
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(true);
  const [quietHoursStart, setQuietHoursStart] = useState("22:00");
  const [quietHoursEnd, setQuietHoursEnd] = useState("08:00");

  const handleSaveNotifications = () => {
    // Here you would typically save to your backend/database
    console.log("Saving notification settings...", {
      emailNotifications,
      pushNotifications,
      leadNotifications,
      meetingReminders,
      systemUpdates,
      notificationFrequency,
      quietHoursEnabled,
      quietHoursStart,
      quietHoursEnd,
    });
    // Show success message or toast
    alert("Notification settings saved successfully!");
  };

  // Checkbox handlers to handle CheckedState type
  const handleEmailNotificationsChange = (
    checked: boolean | "indeterminate"
  ) => {
    setEmailNotifications(checked === true);
  };

  const handlePushNotificationsChange = (
    checked: boolean | "indeterminate"
  ) => {
    setPushNotifications(checked === true);
  };

  const handleLeadNotificationsChange = (
    checked: boolean | "indeterminate"
  ) => {
    setLeadNotifications(checked === true);
  };

  const handleMeetingRemindersChange = (checked: boolean | "indeterminate") => {
    setMeetingReminders(checked === true);
  };

  const handleSystemUpdatesChange = (checked: boolean | "indeterminate") => {
    setSystemUpdates(checked === true);
  };

  const handleQuietHoursChange = (checked: boolean | "indeterminate") => {
    setQuietHoursEnabled(checked === true);
  };

  return (
    <div className="p-6 pr-6 pb-0">
      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
          <CardDescription>
            Configure your integrations and notification preferences
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="space-y-6"
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger
                value="integrations"
                className="flex items-center gap-2"
              >
                <IconPlug className="h-4 w-4" />
                Integrations
              </TabsTrigger>
              <TabsTrigger
                value="notifications"
                className="flex items-center gap-2"
              >
                <IconBell className="h-4 w-4" />
                Notifications
              </TabsTrigger>
            </TabsList>

            <TabsContent value="integrations" className="space-y-6">
              <IntegrationsSettings />
            </TabsContent>

            <TabsContent value="notifications" className="space-y-6">
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium mb-4">
                    Notification Channels
                  </h3>
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="email-notifications"
                        checked={emailNotifications}
                        onCheckedChange={handleEmailNotificationsChange}
                      />
                      <div className="grid gap-1.5 leading-none">
                        <Label
                          htmlFor="email-notifications"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          Email Notifications
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          Receive notifications via email
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="push-notifications"
                        checked={pushNotifications}
                        onCheckedChange={handlePushNotificationsChange}
                      />
                      <div className="grid gap-1.5 leading-none">
                        <Label
                          htmlFor="push-notifications"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          Push Notifications
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          Receive browser push notifications
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-4">
                    Notification Types
                  </h3>
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="lead-notifications"
                        checked={leadNotifications}
                        onCheckedChange={handleLeadNotificationsChange}
                      />
                      <div className="grid gap-1.5 leading-none">
                        <Label
                          htmlFor="lead-notifications"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          New Lead Notifications
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          Get notified when new leads are captured
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="meeting-reminders"
                        checked={meetingReminders}
                        onCheckedChange={handleMeetingRemindersChange}
                      />
                      <div className="grid gap-1.5 leading-none">
                        <Label
                          htmlFor="meeting-reminders"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          Meeting Reminders
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          Receive reminders for upcoming meetings
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="system-updates"
                        checked={systemUpdates}
                        onCheckedChange={handleSystemUpdatesChange}
                      />
                      <div className="grid gap-1.5 leading-none">
                        <Label
                          htmlFor="system-updates"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          System Updates
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          Get notified about system updates and maintenance
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-4">
                    Notification Frequency
                  </h3>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="frequency">
                        How often would you like to receive notifications?
                      </Label>
                      <Select
                        value={notificationFrequency}
                        onValueChange={setNotificationFrequency}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select frequency" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="realtime">Real-time</SelectItem>
                          <SelectItem value="hourly">Hourly digest</SelectItem>
                          <SelectItem value="daily">Daily digest</SelectItem>
                          <SelectItem value="weekly">Weekly digest</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-4">Quiet Hours</h3>
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="quiet-hours"
                        checked={quietHoursEnabled}
                        onCheckedChange={handleQuietHoursChange}
                      />
                      <div className="grid gap-1.5 leading-none">
                        <Label
                          htmlFor="quiet-hours"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          Enable Quiet Hours
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          Disable notifications during specified hours
                        </p>
                      </div>
                    </div>

                    {quietHoursEnabled && (
                      <div className="grid grid-cols-2 gap-4 ml-6">
                        <div className="space-y-2">
                          <Label htmlFor="quiet-start">Start Time</Label>
                          <Select
                            value={quietHoursStart}
                            onValueChange={setQuietHoursStart}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {Array.from({ length: 24 }, (_, i) => {
                                const hour = i.toString().padStart(2, "0");
                                return (
                                  <SelectItem
                                    key={`${hour}:00`}
                                    value={`${hour}:00`}
                                  >
                                    {hour}:00
                                  </SelectItem>
                                );
                              })}
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="quiet-end">End Time</Label>
                          <Select
                            value={quietHoursEnd}
                            onValueChange={setQuietHoursEnd}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {Array.from({ length: 24 }, (_, i) => {
                                const hour = i.toString().padStart(2, "0");
                                return (
                                  <SelectItem
                                    key={`${hour}:00`}
                                    value={`${hour}:00`}
                                  >
                                    {hour}:00
                                  </SelectItem>
                                );
                              })}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex justify-end pt-4">
                  <Button onClick={handleSaveNotifications}>
                    Save Notification Settings
                  </Button>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
