"use client";

import * as React from "react";
import { useState } from "react";
import { Search, Plus, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useLeads } from "@/hooks/use-leads";

interface Lead {
  id: string;
  name: string;
  email: string;
  company: string;
  phone?: string;
  status: string;
  qualified: boolean;
  contacted: boolean;
  meeting_scheduled: boolean;
  source?: string;
  created_at: string;
}

interface DataTableProps {
  showHeader?: boolean;
  title?: string;
  description?: string;
}

export function DataTable({
  showHeader = false,
  title = "Leads",
  description,
}: DataTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const { leads, isLoading, error, refetch } = useLeads();

  // Filter leads based on search term
  const filteredLeads = leads.filter(
    (lead) =>
      lead.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.company.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("es-ES", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadge = (lead: Lead) => {
    if (lead.meeting_scheduled) {
      return <Badge variant="default">Meeting Scheduled</Badge>;
    }
    if (lead.contacted) {
      return <Badge variant="secondary">Contacted</Badge>;
    }
    if (lead.qualified) {
      return <Badge variant="outline">Qualified</Badge>;
    }
    return <Badge variant="secondary">New</Badge>;
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>
            {description || "Loading leads data..."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-24">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>Error loading leads data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-red-500 mb-4">{error.message}</p>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
          {description || "A list of all leads in the system."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search by name, email, or company..."
              className="pl-8 w-full"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Lead
            </Button>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </div>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Lead</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredLeads.length > 0 ? (
              filteredLeads.map((lead) => (
                <TableRow key={lead.id}>
                  <TableCell>
                    <div className="font-medium">{lead.name}</div>
                    {lead.phone && (
                      <div className="text-sm text-muted-foreground">
                        {lead.phone}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>{lead.company}</TableCell>
                  <TableCell>
                    <a
                      href={`mailto:${lead.email}`}
                      className="text-blue-600 hover:text-blue-800 underline"
                    >
                      {lead.email}
                    </a>
                  </TableCell>
                  <TableCell>{getStatusBadge(lead)}</TableCell>
                  <TableCell>{formatDate(lead.created_at)}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">
                        View
                      </Button>
                      <Button variant="ghost" size="sm">
                        Edit
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center">
                  {searchTerm
                    ? "No leads found matching your search."
                    : "No leads found."}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {filteredLeads.length > 0 && (
          <div className="flex items-center justify-between space-x-2 py-4">
            <div className="flex-1 text-sm text-muted-foreground">
              Showing {filteredLeads.length} of {leads.length} lead(s)
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
