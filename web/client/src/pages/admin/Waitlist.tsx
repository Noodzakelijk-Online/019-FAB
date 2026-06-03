import { trpc } from "@/lib/trpc";
import { useState, useMemo } from "react";
import { Download, Search, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import AdminLayout from "@/components/AdminLayout";

export default function AdminWaitlist() {
  const waitlistEntries = trpc.waitlist.list.useQuery();
  const waitlistStats = trpc.waitlist.stats.useQuery();
  const [search, setSearch] = useState("");
  const [situationFilter, setSituationFilter] = useState("all");

  const filtered = useMemo(() => {
    if (!waitlistEntries.data) return [];
    return waitlistEntries.data.filter((entry) => {
      const matchSearch =
        !search ||
        entry.email.toLowerCase().includes(search.toLowerCase()) ||
        (entry.firstName || "").toLowerCase().includes(search.toLowerCase()) ||
        (entry.lastName || "").toLowerCase().includes(search.toLowerCase());
      const matchSituation =
        situationFilter === "all" || entry.source === situationFilter;
      return matchSearch && matchSituation;
    });
  }, [waitlistEntries.data, search, situationFilter]);

  function exportCSV() {
    if (!filtered.length) return;
    const headers = ["Email", "First Name", "Last Name", "Source", "Signed Up"];
    const rows = filtered.map((e) => [
      e.email,
      e.firstName || "",
      e.lastName || "",
      e.source || "",
      new Date(e.createdAt).toISOString(),
    ]);
    const csv = [headers, ...rows].map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fab-waitlist-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-charcoal">Waitlist</h1>
            <p className="text-charcoal-light mt-1">
              {waitlistEntries.data?.length ?? 0} total signups
            </p>
          </div>
          <Button
            onClick={exportCSV}
            variant="outline"
            className="rounded-xl border-teal/20 text-teal hover:bg-teal/5"
            disabled={!filtered.length}
          >
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        </div>

        {/* Growth Chart (simple bar visualization) */}
        {waitlistStats.data?.daily && waitlistStats.data.daily.length > 0 && (
          <div className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm p-6">
            <h2 className="text-sm font-medium text-charcoal-light mb-4">Signup Growth</h2>
            <div className="flex items-end gap-1 h-24">
              {waitlistStats.data.daily.slice(-30).map((day, i) => {
                const maxCount = Math.max(
                  ...waitlistStats.data!.daily.slice(-30).map((d) => d.count)
                );
                const height = maxCount > 0 ? (day.count / maxCount) * 100 : 0;
                return (
                  <div
                    key={i}
                    className="flex-1 bg-teal/20 hover:bg-teal/40 rounded-t transition-colors relative group"
                    style={{ height: `${Math.max(height, 4)}%` }}
                    title={`${day.date}: ${day.count} signups`}
                  >
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-charcoal text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                      {day.date}: {day.count}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="flex justify-between mt-2 text-xs text-charcoal-light">
              <span>{waitlistStats.data.daily[Math.max(0, waitlistStats.data.daily.length - 30)]?.date}</span>
              <span>{waitlistStats.data.daily[waitlistStats.data.daily.length - 1]?.date}</span>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-charcoal-light" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
            />
          </div>
          <select
            value={situationFilter}
            onChange={(e) => setSituationFilter(e.target.value)}
            className="px-4 py-2.5 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
          >
            <option value="all">All Sources</option>
            <option value="website">Website</option>
          </select>
        </div>

        {/* Table */}
        <div className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
          {waitlistEntries.isLoading ? (
            <div className="p-12 text-center text-charcoal-light">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="p-12 text-center">
              <Users className="w-12 h-12 text-sand-dark/40 mx-auto mb-4" />
              <p className="text-charcoal-light">
                {search || situationFilter !== "all"
                  ? "No entries match your filters"
                  : "No waitlist signups yet"}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-sand-dark/10">
                    <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-6 py-3">
                      Name
                    </th>
                    <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-6 py-3">
                      Email
                    </th>
                    <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-6 py-3">
                      Source
                    </th>
                    <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-6 py-3">
                      Signed Up
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-sand-dark/10">
                  {filtered.map((entry) => (
                    <tr key={entry.id} className="hover:bg-sand/20 transition-colors">
                      <td className="px-6 py-3.5 text-sm text-charcoal">
                        {entry.firstName || entry.lastName
                          ? `${entry.firstName || ""} ${entry.lastName || ""}`.trim()
                          : "—"}
                      </td>
                      <td className="px-6 py-3.5 text-sm text-charcoal">{entry.email}</td>
                      <td className="px-6 py-3.5">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sage-light text-sage">
                          {entry.source || "website"}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-sm text-charcoal-light">
                        {new Date(entry.createdAt).toLocaleDateString("en-US", {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}
