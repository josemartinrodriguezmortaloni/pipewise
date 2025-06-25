"use client";

import { useState, useEffect, useCallback } from "react";
import { AppSidebar } from "@/components/app-sidebar";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

import {
  Mail,
  MessageCircle,
  Calendar,
  ExternalLink,
  Filter,
  Search,
  User,
  AtSign,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import React from "react";

interface Contact {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  platform: "whatsapp" | "instagram" | "twitter" | "email";
  platform_id: string;
  username?: string;
  profile_url?: string;
  created_at: string;
  total_messages: number;
  last_message_at?: string;
  meeting_scheduled: boolean;
  meeting_url?: string;
  last_contact_date?: string;
}

interface ContactStats {
  total_contacts: number;
  contacts_by_platform: Record<string, number>;
  messages_sent: number;
  meetings_scheduled: number;
  conversion_rate: number;
  last_contact_date?: string;
}

interface Message {
  id: string;
  platform: string;
  message_type: string;
  subject?: string;
  content: string;
  template_name?: string;
  sent_at: string;
  status: string;
  metadata?: Record<string, unknown>;
}

const platformIcons = {
  whatsapp: MessageCircle,
  instagram: AtSign,
  twitter: AtSign,
  email: Mail,
};

const platformColors = {
  whatsapp: "bg-green-100 text-green-800",
  instagram: "bg-pink-100 text-pink-800",
  twitter: "bg-blue-100 text-blue-800",
  email: "bg-gray-100 text-gray-800",
};

function ContactedPageContent() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [stats, setStats] = useState<ContactStats | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [platformFilter, setPlatformFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedContactId, setSelectedContactId] = useState<string | null>(
    null
  );
  const [contactMessages, setContactMessages] = useState<Message[]>([]);

  // Memoize callback functions to prevent re-creation on every render
  const onContactsSuccess = useCallback((data: { contacts: Contact[] }) => {
    setContacts(data.contacts || []);
  }, []);

  const onStatsSuccess = useCallback((data: ContactStats) => {
    setStats(data);
  }, []);

  const onStatsError = useCallback(() => {
    setStats(null);
  }, []);

  const onMessagesSuccess = useCallback((data: { messages: Message[] }) => {
    setContactMessages(data.messages || []);
  }, []);

  // API Hooks
  const {
    loading: loadingContacts,
    error: contactsError,
    execute: fetchContacts,
  } = useApi<{ contacts: Contact[] }>(
    "/contacts",
    {},
    {
      onSuccess: onContactsSuccess,
    }
  );

  const {
    loading: loadingStats,
    error: statsError,
    execute: fetchStats,
  } = useApi<ContactStats>(
    "/contacts/stats",
    {},
    {
      onSuccess: onStatsSuccess,
      onError: onStatsError,
    }
  );

  const { loading: messagesApiLoading, execute: fetchContactMessagesApi } =
    useApi<{ messages: Message[] }>(
      `/contacts/${selectedContactId}/messages`,
      {},
      {
        onSuccess: onMessagesSuccess,
        onError: () => setContactMessages([]),
      }
    );

  useEffect(() => {
    const params = new URLSearchParams();
    if (platformFilter !== "all") {
      params.append("platform", platformFilter);
    }
    const queryString = params.toString();
    fetchContacts(queryString ? `/contacts?${queryString}` : "/contacts");
  }, [platformFilter, fetchContacts]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const fetchContactMessages = async (contactId: string) => {
    if (selectedContactId === contactId) {
      setSelectedContactId(null);
      setContactMessages([]);
    } else {
      setSelectedContactId(contactId);
      // The endpoint in useApi is dynamic, but we need to trigger it for a specific ID
      await fetchContactMessagesApi(`/contacts/${contactId}/messages`);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("es-ES", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const filteredContacts = contacts.filter((contact) => {
    const matchesSearch =
      contact.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      contact.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      contact.username?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "scheduled" && contact.meeting_scheduled) ||
      (statusFilter === "pending" && !contact.meeting_scheduled);

    return matchesSearch && matchesStatus;
  });

  const isLoading = loadingContacts || loadingStats;
  const pageError = contactsError || statsError;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Loading data...</p>
        </div>
      </div>
    );
  }

  if (pageError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-red-500">
          <p>{pageError.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Filters and Search */}
      <div className="p-6 pr-6 bg-background border-b sticky top-0 z-10">
        <div className="flex items-center gap-4 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search by name, email, or username..."
              className="pl-8 w-full"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <Select value={platformFilter} onValueChange={setPlatformFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by platform" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Platforms</SelectItem>
                <SelectItem value="whatsapp">WhatsApp</SelectItem>
                <SelectItem value="instagram">Instagram</SelectItem>
                <SelectItem value="twitter">Twitter</SelectItem>
                <SelectItem value="email">Email</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="scheduled">Meeting Scheduled</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 pr-6 pb-0">
        {stats && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Contacts
                </CardTitle>
                <User className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_contacts}</div>
                <p className="text-xs text-muted-foreground">
                  Across all platforms
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Meetings Scheduled
                </CardTitle>
                <Calendar className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats.meetings_scheduled}
                </div>
                <p className="text-xs text-muted-foreground">
                  {stats.conversion_rate.toFixed(1)}% conversion rate
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Messages Sent
                </CardTitle>
                <MessageCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.messages_sent}</div>
                <p className="text-xs text-muted-foreground">
                  Total outbound messages
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Contact List</CardTitle>
            <CardDescription>A list of all contacted users.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Contact</TableHead>
                  <TableHead>Platform</TableHead>
                  <TableHead>Last Activity</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredContacts.map((contact) => (
                  <React.Fragment key={contact.id}>
                    <TableRow>
                      <TableCell>
                        <div className="font-medium">{contact.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {contact.email || contact.username}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`${
                            platformColors[
                              contact.platform as keyof typeof platformColors
                            ]
                          }`}
                        >
                          {platformIcons[
                            contact.platform as keyof typeof platformIcons
                          ] && <MessageCircle className="mr-1 h-3 w-3" />}
                          {contact.platform}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {contact.last_message_at
                          ? formatDate(contact.last_message_at)
                          : "N/A"}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            contact.meeting_scheduled ? "default" : "secondary"
                          }
                        >
                          {contact.meeting_scheduled
                            ? "Meeting Scheduled"
                            : "Pending"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => fetchContactMessages(contact.id)}
                          >
                            <Mail className="mr-2 h-4 w-4" />
                            {selectedContactId === contact.id
                              ? "Hide Messages"
                              : "View Messages"}
                          </Button>
                          {contact.profile_url && (
                            <Button variant="ghost" size="sm" asChild>
                              <a
                                href={contact.profile_url}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                <ExternalLink className="h-4 w-4" />
                              </a>
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                    {selectedContactId === contact.id && (
                      <TableRow>
                        <TableCell colSpan={5}>
                          {messagesApiLoading ? (
                            <p>Loading messages...</p>
                          ) : (
                            <div className="p-4 bg-muted/50 rounded-lg">
                              <h4 className="font-semibold mb-2">
                                Message History for {contact.name}
                              </h4>
                              {contactMessages.length > 0 ? (
                                <ul className="space-y-4">
                                  {contactMessages.map((msg) => (
                                    <li
                                      key={msg.id}
                                      className="p-3 bg-background rounded-md border"
                                    >
                                      <div className="flex justify-between items-center mb-1">
                                        <span className="font-semibold text-sm">
                                          {msg.subject || "Message"}
                                        </span>
                                        <span className="text-xs text-muted-foreground">
                                          {formatDate(msg.sent_at)}
                                        </span>
                                      </div>
                                      <p className="text-sm text-muted-foreground">
                                        {msg.content}
                                      </p>
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p>No messages found for this contact.</p>
                              )}
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function ContactedPage() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="m-0 rounded-none shadow-none">
        <div className="flex flex-1 flex-col h-screen overflow-hidden">
          <header className="sticky top-0 z-40 flex h-12 shrink-0 items-center gap-2 bg-background px-4">
            <SidebarTrigger />
          </header>
          <main className="flex-1 overflow-y-auto">
            <ContactedPageContent />
          </main>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
