import { trpc } from "@/lib/trpc";
import { useState } from "react";
import {
  MessageSquare,
  Mail,
  Clock,
  CheckCircle2,
  Archive,
  ChevronDown,
  ChevronUp,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import AdminLayout from "@/components/AdminLayout";
import { toast } from "sonner";

const statusConfig = {
  new: { label: "New", color: "bg-teal/10 text-teal", icon: Mail },
  read: { label: "Read", color: "bg-sand text-charcoal", icon: Clock },
  replied: { label: "Replied", color: "bg-sage-light text-sage", icon: CheckCircle2 },
  archived: { label: "Archived", color: "bg-charcoal/10 text-charcoal-light", icon: Archive },
};

type MessageStatus = keyof typeof statusConfig;

export default function AdminMessages() {
  const utils = trpc.useUtils();
  const contactMessages = trpc.contact.list.useQuery({});
  const updateStatus = trpc.contact.updateStatus.useMutation({
    onSuccess: () => {
      utils.contact.list.invalidate();
      utils.contact.count.invalidate();
      toast.success("Status updated");
    },
  });

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | MessageStatus>("all");
  const [search, setSearch] = useState("");

  const filtered = (contactMessages.data ?? []).filter((msg) => {
    const matchStatus = statusFilter === "all" || msg.status === statusFilter;
    const matchSearch =
      !search ||
      msg.firstName.toLowerCase().includes(search.toLowerCase()) ||
      msg.lastName.toLowerCase().includes(search.toLowerCase()) ||
      msg.email.toLowerCase().includes(search.toLowerCase()) ||
      msg.subject.toLowerCase().includes(search.toLowerCase()) ||
      msg.message.toLowerCase().includes(search.toLowerCase());
    return matchStatus && matchSearch;
  });

  function handleExpand(id: number, currentStatus: string) {
    setExpandedId(expandedId === id ? null : id);
    // Auto-mark as read when expanding a new message
    if (currentStatus === "new" && expandedId !== id) {
      updateStatus.mutate({ id, status: "read" });
    }
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-semibold text-charcoal">Messages</h1>
          <p className="text-charcoal-light mt-1">
            {contactMessages.data?.length ?? 0} total messages
            {contactMessages.data?.filter((m) => m.status === "new").length
              ? ` · ${contactMessages.data.filter((m) => m.status === "new").length} unread`
              : ""}
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-charcoal-light" />
            <input
              type="text"
              placeholder="Search messages..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
            />
          </div>
          <div className="flex gap-2">
            {(["all", "new", "read", "replied", "archived"] as const).map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-2 rounded-xl text-sm transition-all ${
                  statusFilter === status
                    ? "bg-teal text-white"
                    : "bg-white border border-sand-dark/30 text-charcoal-light hover:border-teal/30"
                }`}
              >
                {status === "all" ? "All" : statusConfig[status].label}
              </button>
            ))}
          </div>
        </div>

        {/* Message List */}
        <div className="space-y-3">
          {contactMessages.isLoading ? (
            <div className="bg-white rounded-2xl border border-sand-dark/15 p-12 text-center text-charcoal-light">
              Loading...
            </div>
          ) : filtered.length === 0 ? (
            <div className="bg-white rounded-2xl border border-sand-dark/15 p-12 text-center">
              <MessageSquare className="w-12 h-12 text-sand-dark/40 mx-auto mb-4" />
              <p className="text-charcoal-light">
                {search || statusFilter !== "all"
                  ? "No messages match your filters"
                  : "No contact messages yet"}
              </p>
            </div>
          ) : (
            filtered.map((msg) => {
              const isExpanded = expandedId === msg.id;
              const config = statusConfig[msg.status as MessageStatus] || statusConfig.new;
              return (
                <div
                  key={msg.id}
                  className={`bg-white rounded-2xl border shadow-sm overflow-hidden transition-all ${
                    msg.status === "new"
                      ? "border-teal/30"
                      : "border-sand-dark/15"
                  }`}
                >
                  {/* Message header (clickable) */}
                  <button
                    onClick={() => handleExpand(msg.id, msg.status)}
                    className="w-full text-left px-6 py-4 flex items-center gap-4 hover:bg-sand/20 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-medium text-charcoal text-sm">
                          {msg.firstName} {msg.lastName}
                        </span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
                          {config.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-charcoal font-medium truncate">{msg.subject}</span>
                        {!isExpanded && (
                          <span className="text-charcoal-light truncate">
                            — {msg.message.slice(0, 80)}...
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs text-charcoal-light">
                        {new Date(msg.createdAt).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-charcoal-light" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-charcoal-light" />
                      )}
                    </div>
                  </button>

                  {/* Expanded content */}
                  {isExpanded && (
                    <div className="px-6 pb-5 border-t border-sand-dark/10">
                      <div className="pt-4 space-y-4">
                        <div className="flex items-center gap-4 text-sm text-charcoal-light">
                          <span className="flex items-center gap-1.5">
                            <Mail className="w-3.5 h-3.5" />
                            {msg.email}
                          </span>
                          <span className="flex items-center gap-1.5">
                            <Clock className="w-3.5 h-3.5" />
                            {new Date(msg.createdAt).toLocaleString()}
                          </span>
                        </div>
                        <div className="bg-sand/30 rounded-xl p-4 text-sm text-charcoal leading-relaxed whitespace-pre-wrap">
                          {msg.message}
                        </div>
                        <div className="flex items-center gap-2 pt-2">
                          <span className="text-xs text-charcoal-light mr-2">Set status:</span>
                          {(["read", "replied", "archived"] as const).map((status) => (
                            <Button
                              key={status}
                              variant="outline"
                              size="sm"
                              className={`rounded-lg text-xs ${
                                msg.status === status
                                  ? "bg-teal/10 border-teal/30 text-teal"
                                  : "border-sand-dark/30 text-charcoal-light hover:border-teal/30"
                              }`}
                              onClick={() => updateStatus.mutate({ id: msg.id, status })}
                              disabled={msg.status === status}
                            >
                              {statusConfig[status].label}
                            </Button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </AdminLayout>
  );
}
