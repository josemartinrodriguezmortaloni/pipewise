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
  Phone,
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
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [platformFilter, setPlatformFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedContactId, setSelectedContactId] = useState<string | null>(
    null
  );
  const [contactMessages, setContactMessages] = useState<Message[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchContacts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      if (platformFilter !== "all") {
        params.append("platform", platformFilter);
      }

      const response = await fetch(`/api/contacts?${params}`, {
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error(`Contacts fetch failed: ${response.status}`);
      }
      const data = await response.json();
      setContacts(data.contacts || []);
    } catch (error) {
      console.error("Error fetching contacts:", error);
      setError("Failed to load contacts. Please try again later.");
    } finally {
      setLoading(false);
    }
  }, [platformFilter]);

  const fetchStats = async () => {
    try {
      const response = await fetch("/api/contacts/stats");
      if (!response.ok) {
        throw new Error(`Stats fetch failed: ${response.status}`);
      }
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error("Error fetching stats:", error);
      setStats(null); // Clear stats on error
    }
  };

  useEffect(() => {
    fetchContacts();
    fetchStats();
  }, [fetchContacts]);

  const fetchContactMessages = async (contactId: string) => {
    try {
      setLoadingMessages(true);
      const response = await fetch(`/api/contacts/${contactId}/messages`);
      const data = await response.json();
      setContactMessages(data.messages || []);
    } catch (error) {
      console.error("Error fetching contact messages:", error);
      setContactMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  const handleViewMessages = (contact: Contact) => {
    if (selectedContactId === contact.id) {
      // Si ya está seleccionado, lo cerramos
      setSelectedContactId(null);
      setContactMessages([]);
    } else {
      // Seleccionar nuevo contacto y cargar sus mensajes
      setSelectedContactId(contact.id);
      fetchContactMessages(contact.id);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando contactos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-red-500">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Filters and Search */}
      <div className="p-4 bg-background border-b sticky top-0 z-10">
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

      <div className="flex-1 overflow-auto p-4">
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
                  <>
                    <TableRow key={contact.id}>
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
                            onClick={() => handleViewMessages(contact)}
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
                          {loadingMessages ? (
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
                  </>
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
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset>
        <div className="flex flex-1 flex-col h-screen overflow-hidden">
          <header className="sticky top-0 z-40 flex h-[--header-height] shrink-0 items-center gap-2 bg-background/80 px-4 backdrop-blur lg:px-6">
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
