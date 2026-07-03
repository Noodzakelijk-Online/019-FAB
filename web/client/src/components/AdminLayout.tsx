import { useAuth } from "@/_core/hooks/useAuth";
import { getLoginUrl } from "@/const";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  LogOut,
  ChevronLeft,
  Menu,
  Shield,
  FileText,
  FileSearch,
} from "lucide-react";
import { Link, useLocation } from "wouter";
import { useState } from "react";

const navItems = [
  { icon: LayoutDashboard, label: "Overview", path: "/admin" },
  { icon: FileSearch, label: "Operations", path: "/admin/operations" },
  { icon: Users, label: "Waitlist", path: "/admin/waitlist" },
  { icon: MessageSquare, label: "Messages", path: "/admin/messages" },
  { icon: FileText, label: "Blog", path: "/admin/blog" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const [location] = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  if (loading) {
    return (
      <div className="min-h-screen bg-warm-white flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-sand" />
          <div className="w-32 h-4 rounded bg-sand" />
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-warm-white flex items-center justify-center">
        <div className="max-w-md w-full p-8 text-center">
          <div className="w-16 h-16 rounded-2xl bg-teal/10 flex items-center justify-center mx-auto mb-6">
            <Shield className="w-8 h-8 text-teal" />
          </div>
          <h1 className="text-2xl text-charcoal mb-3">Admin Access Required</h1>
          <p className="text-charcoal-light mb-8">
            Please sign in with an admin account to access the dashboard.
          </p>
          <Button
            onClick={() => { window.location.href = getLoginUrl(); }}
            className="bg-teal hover:bg-teal-light text-white px-8 py-5 rounded-xl"
          >
            Sign In
          </Button>
        </div>
      </div>
    );
  }

  if (user.role !== "admin") {
    return (
      <div className="min-h-screen bg-warm-white flex items-center justify-center">
        <div className="max-w-md w-full p-8 text-center">
          <div className="w-16 h-16 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-6">
            <Shield className="w-8 h-8 text-red-500" />
          </div>
          <h1 className="text-2xl text-charcoal mb-3">Access Denied</h1>
          <p className="text-charcoal-light mb-8">
            You don't have permission to access the admin dashboard.
          </p>
          <Link href="/">
            <Button variant="outline" className="rounded-xl border-teal/20 text-teal hover:bg-teal/5 px-8 py-5">
              Back to Home
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-warm-white flex">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? "w-64" : "w-16"
        } bg-white border-r border-sand-dark/15 flex flex-col transition-all duration-300 shrink-0 sticky top-0 h-screen`}
      >
        {/* Sidebar header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-sand-dark/10">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-teal flex items-center justify-center">
                <span className="text-white font-bold text-sm">F</span>
              </div>
              <span className="font-semibold text-charcoal text-sm">FAB Admin</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-8 h-8 rounded-lg hover:bg-sand/50 flex items-center justify-center transition-colors"
          >
            {sidebarOpen ? (
              <ChevronLeft className="w-4 h-4 text-charcoal-light" />
            ) : (
              <Menu className="w-4 h-4 text-charcoal-light" />
            )}
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex-1 py-3 px-2">
          {navItems.map((item) => {
            const isActive = location === item.path;
            return (
              <Link key={item.path} href={item.path}>
                <button
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl mb-1 transition-all text-sm ${
                    isActive
                      ? "bg-teal/10 text-teal font-medium"
                      : "text-charcoal-light hover:bg-sand/40 hover:text-charcoal"
                  }`}
                >
                  <item.icon className={`w-5 h-5 shrink-0 ${isActive ? "text-teal" : ""}`} />
                  {sidebarOpen && <span>{item.label}</span>}
                </button>
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-3 border-t border-sand-dark/10">
          {sidebarOpen ? (
            <div className="flex items-center gap-3 px-2 py-2">
              <div className="w-8 h-8 rounded-full bg-teal/10 flex items-center justify-center shrink-0">
                <span className="text-teal text-xs font-semibold">
                  {user.name?.charAt(0)?.toUpperCase() || "A"}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-charcoal truncate">{user.name || "Admin"}</p>
                <p className="text-xs text-charcoal-light truncate">{user.email || ""}</p>
              </div>
              <button
                onClick={logout}
                className="w-8 h-8 rounded-lg hover:bg-red-50 flex items-center justify-center transition-colors"
                title="Sign out"
              >
                <LogOut className="w-4 h-4 text-charcoal-light hover:text-red-500" />
              </button>
            </div>
          ) : (
            <button
              onClick={logout}
              className="w-full flex items-center justify-center py-2"
              title="Sign out"
            >
              <LogOut className="w-4 h-4 text-charcoal-light" />
            </button>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
