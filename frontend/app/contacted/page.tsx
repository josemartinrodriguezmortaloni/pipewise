"use client";

import { useState, useEffect, useCallback } from "react";
import { AppSidebar } from "@/components/app-sidebar";
import { SiteHeader } from "@/components/site-header";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
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

  const fetchContacts = useCallback(async () => {
    try {
      setLoading(true);
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
    } finally {
      setLoading(false);
    }
  }, [platformFilter]);

  const fetchStats = async () => {
    try {
      const response = await fetch("/api/contacts/stats");
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error("Error fetching stats:", error);
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

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Personas Contactadas
          </h1>
          <p className="text-gray-600 mt-1">
            Gestiona todos los contactos realizados a través de diferentes
            plataformas
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-2xl font-bold">
                {stats.total_contacts}
              </CardTitle>
              <CardDescription>Total Contactados</CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-2xl font-bold">
                {stats.messages_sent}
              </CardTitle>
              <CardDescription>Mensajes Enviados</CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-2xl font-bold">
                {stats.meetings_scheduled}
              </CardTitle>
              <CardDescription>Reuniones Agendadas</CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-2xl font-bold">
                {stats.conversion_rate?.toFixed(1) || 0}%
              </CardTitle>
              <CardDescription>Tasa de Conversión</CardDescription>
            </CardHeader>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Buscar por nombre, email o username..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        <Select value={platformFilter} onValueChange={setPlatformFilter}>
          <SelectTrigger className="w-[180px]">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Plataforma" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas las plataformas</SelectItem>
            <SelectItem value="email">Email</SelectItem>
            <SelectItem value="whatsapp">WhatsApp</SelectItem>
            <SelectItem value="instagram">Instagram</SelectItem>
            <SelectItem value="twitter">Twitter</SelectItem>
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <Calendar className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los estados</SelectItem>
            <SelectItem value="scheduled">Con reunión agendada</SelectItem>
            <SelectItem value="pending">Sin reunión agendada</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Contacts Table */}
      <Card>
        <CardHeader>
          <CardTitle>Contactos ({filteredContacts.length})</CardTitle>
          <CardDescription>
            Lista de todas las personas contactadas a través de diferentes
            plataformas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Contacto</TableHead>
                <TableHead>Plataforma</TableHead>
                <TableHead>Información</TableHead>
                <TableHead>Mensajes</TableHead>
                <TableHead>Último Contacto</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredContacts.map((contact) => {
                const PlatformIcon = platformIcons[contact.platform];
                return (
                  <TableRow key={contact.id}>
                    <TableCell>
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                          <User className="w-4 h-4 text-gray-600" />
                        </div>
                        <div>
                          <div className="font-medium">{contact.name}</div>
                          <div className="text-sm text-gray-500">
                            {contact.email || contact.username || contact.phone}
                          </div>
                        </div>
                      </div>
                    </TableCell>

                    <TableCell>
                      <Badge className={platformColors[contact.platform]}>
                        <PlatformIcon className="w-3 h-3 mr-1" />
                        {contact.platform}
                      </Badge>
                    </TableCell>

                    <TableCell>
                      <div className="space-y-1 text-sm">
                        {contact.email && (
                          <div className="flex items-center">
                            <Mail className="w-3 h-3 mr-1 text-gray-400" />
                            {contact.email}
                          </div>
                        )}
                        {contact.phone && (
                          <div className="flex items-center">
                            <Phone className="w-3 h-3 mr-1 text-gray-400" />
                            {contact.phone}
                          </div>
                        )}
                        {contact.username && (
                          <div className="flex items-center">
                            <AtSign className="w-3 h-3 mr-1 text-gray-400" />@
                            {contact.username}
                          </div>
                        )}
                      </div>
                    </TableCell>

                    <TableCell>
                      <Badge variant="outline">
                        {contact.total_messages} mensaje
                        {contact.total_messages !== 1 ? "s" : ""}
                      </Badge>
                    </TableCell>

                    <TableCell>
                      {contact.last_message_at ? (
                        <div className="text-sm">
                          {formatDate(contact.last_message_at)}
                        </div>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </TableCell>

                    <TableCell>
                      {contact.meeting_scheduled ? (
                        <Badge className="bg-green-100 text-green-800">
                          Reunión agendada
                        </Badge>
                      ) : (
                        <Badge variant="outline">Pendiente</Badge>
                      )}
                    </TableCell>

                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          variant={
                            selectedContactId === contact.id
                              ? "default"
                              : "outline"
                          }
                          size="sm"
                          onClick={() => handleViewMessages(contact)}
                        >
                          {selectedContactId === contact.id
                            ? "Ocultar mensajes"
                            : "Ver mensajes"}
                        </Button>

                        {contact.meeting_url && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              window.open(contact.meeting_url, "_blank")
                            }
                          >
                            <ExternalLink className="w-3 h-3 mr-1" />
                            Reunión
                          </Button>
                        )}

                        {contact.profile_url && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              window.open(contact.profile_url, "_blank")
                            }
                          >
                            <ExternalLink className="w-3 h-3 mr-1" />
                            Perfil
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {filteredContacts.length === 0 && (
            <div className="text-center py-8">
              <User className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                No hay contactos
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                {searchTerm ||
                platformFilter !== "all" ||
                statusFilter !== "all"
                  ? "No se encontraron contactos que coincidan con los filtros."
                  : "Aún no has contactado a ninguna persona."}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Sección de mensajes expandible */}
      {selectedContactId && (
        <Card>
          <CardHeader>
            <CardTitle>
              Mensajes de{" "}
              {contacts.find((c) => c.id === selectedContactId)?.name}
            </CardTitle>
            <CardDescription>
              Historial completo de conversación con este contacto
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingMessages ? (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : contactMessages.length > 0 ? (
              <div className="space-y-4">
                {contactMessages.map((message) => (
                  <div
                    key={message.id}
                    className="border rounded-lg p-4 bg-gray-50"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-center space-x-2">
                        <Badge variant="outline" className="text-xs">
                          {message.message_type}
                        </Badge>
                        {message.template_name && (
                          <Badge variant="secondary" className="text-xs">
                            {message.template_name}
                          </Badge>
                        )}
                        <Badge
                          variant={
                            message.status === "sent" ? "default" : "secondary"
                          }
                          className="text-xs"
                        >
                          {message.status}
                        </Badge>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-gray-500">
                          {formatDate(message.sent_at)}
                        </div>
                        <div className="text-xs text-gray-400 capitalize">
                          {message.platform}
                        </div>
                      </div>
                    </div>

                    {message.subject && (
                      <h4 className="font-medium mb-2 text-gray-900">
                        {message.subject}
                      </h4>
                    )}

                    <div className="prose prose-sm max-w-none">
                      <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                        {message.content}
                      </p>
                    </div>

                    {message.metadata &&
                      Object.keys(message.metadata).length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <details className="text-xs text-gray-500">
                            <summary className="cursor-pointer hover:text-gray-700">
                              Detalles técnicos
                            </summary>
                            <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                              {JSON.stringify(message.metadata, null, 2)}
                            </pre>
                          </details>
                        </div>
                      )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <MessageCircle className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">
                  No hay mensajes
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  Aún no se han enviado mensajes a este contacto.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
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
        <SiteHeader />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <ContactedPageContent />
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
