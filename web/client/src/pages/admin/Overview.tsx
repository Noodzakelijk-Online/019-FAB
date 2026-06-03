import { trpc } from "@/lib/trpc";
import { Users, MessageSquare, TrendingUp, Clock, CreditCard, FileText } from "lucide-react";
import AdminLayout from "@/components/AdminLayout";

export default function AdminOverview() {
  const waitlistCount = trpc.waitlist.count.useQuery();
  const waitlistStats = trpc.waitlist.stats.useQuery();
  const contactCount = trpc.contact.count.useQuery();
  const contactMessages = trpc.contact.list.useQuery({});
  const blogCount = trpc.blog.count.useQuery();

  const newMessages = contactMessages.data?.filter((m) => m.status === "new").length ?? 0;

  const stats = [
    {
      label: "Total Waitlist Signups",
      value: waitlistCount.data?.count ?? 0,
      icon: Users,
      color: "bg-teal/10 text-teal",
      change: waitlistStats.data?.daily?.length
        ? `+${waitlistStats.data.daily[waitlistStats.data.daily.length - 1]?.count ?? 0} today`
        : "",
    },
    {
      label: "Contact Messages",
      value: contactCount.data?.count ?? 0,
      icon: MessageSquare,
      color: "bg-sage-light text-sage",
      change: newMessages > 0 ? `${newMessages} unread` : "All read",
    },
    {
      label: "Blog Posts",
      value: blogCount.data?.count ?? 0,
      icon: FileText,
      color: "bg-sand text-charcoal",
      change: "Published & drafts",
    },
    {
      label: "Stripe Integration",
      value: "Active",
      icon: CreditCard,
      color: "bg-teal/10 text-teal",
      change: "Test mode",
    },
  ];

  return (
    <AdminLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-semibold text-charcoal">Dashboard Overview</h1>
          <p className="text-charcoal-light mt-1">
            Monitor your waitlist growth, messages, and content.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {stats.map((stat, i) => (
            <div
              key={i}
              className="bg-white rounded-2xl p-6 border border-sand-dark/15 shadow-sm"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`w-10 h-10 rounded-xl ${stat.color} flex items-center justify-center`}>
                  <stat.icon className="w-5 h-5" />
                </div>
              </div>
              <div className="text-2xl font-semibold text-charcoal mb-1">{stat.value}</div>
              <div className="text-sm text-charcoal-light">{stat.label}</div>
              {stat.change && (
                <div className="text-xs text-sage mt-2">{stat.change}</div>
              )}
            </div>
          ))}
        </div>

        {/* Recent Activity */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Recent Waitlist Signups */}
          <div className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-sand-dark/10">
              <h2 className="text-lg font-semibold text-charcoal">Recent Waitlist Signups</h2>
            </div>
            <div className="divide-y divide-sand-dark/10">
              {waitlistStats.isLoading ? (
                <div className="p-6 text-center text-charcoal-light">Loading...</div>
              ) : (
                <>
                  {(waitlistStats.data as any)?.daily?.slice(-5).reverse().map((day: any, i: number) => (
                    <div key={i} className="px-6 py-3 flex items-center justify-between">
                      <span className="text-sm text-charcoal">{day.date}</span>
                      <span className="text-sm font-medium text-teal">{day.count} signups</span>
                    </div>
                  ))}
                  {(!waitlistStats.data?.daily || waitlistStats.data.daily.length === 0) && (
                    <div className="p-6 text-center text-charcoal-light text-sm">
                      No signups yet
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Recent Messages */}
          <div className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-sand-dark/10">
              <h2 className="text-lg font-semibold text-charcoal">Recent Messages</h2>
            </div>
            <div className="divide-y divide-sand-dark/10">
              {contactMessages.isLoading ? (
                <div className="p-6 text-center text-charcoal-light">Loading...</div>
              ) : (
                <>
                  {contactMessages.data?.slice(0, 5).map((msg) => (
                    <div key={msg.id} className="px-6 py-3 flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-charcoal truncate">
                            {msg.firstName} {msg.lastName}
                          </span>
                          {msg.status === "new" && (
                            <span className="w-2 h-2 rounded-full bg-teal shrink-0" />
                          )}
                        </div>
                        <p className="text-xs text-charcoal-light truncate">{msg.subject}</p>
                      </div>
                      <span className="text-xs text-charcoal-light shrink-0 ml-4">
                        {new Date(msg.createdAt).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                  {(!contactMessages.data || contactMessages.data.length === 0) && (
                    <div className="p-6 text-center text-charcoal-light text-sm">
                      No messages yet
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Stripe Info Card */}
        <div className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-[#635BFF]/10 flex items-center justify-center">
              <CreditCard className="w-5 h-5 text-[#635BFF]" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-charcoal">Stripe Payments</h2>
              <p className="text-xs text-charcoal-light">Pay-As-You-Go subscription management</p>
            </div>
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-sand/30">
              <div className="text-sm text-charcoal-light mb-1">Mode</div>
              <div className="text-sm font-medium text-charcoal">Test Sandbox</div>
            </div>
            <div className="p-4 rounded-xl bg-sand/30">
              <div className="text-sm text-charcoal-light mb-1">Base Price</div>
              <div className="text-sm font-medium text-charcoal">&euro;4.99/month</div>
            </div>
            <div className="p-4 rounded-xl bg-sand/30">
              <div className="text-sm text-charcoal-light mb-1">Webhook</div>
              <div className="text-sm font-medium text-charcoal">Configured</div>
            </div>
          </div>
          <p className="text-xs text-charcoal-light mt-4">
            Manage your Stripe account, view transactions, and configure webhooks in the{" "}
            <a
              href="https://dashboard.stripe.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal hover:underline"
            >
              Stripe Dashboard
            </a>
            .
          </p>
        </div>
      </div>
    </AdminLayout>
  );
}
