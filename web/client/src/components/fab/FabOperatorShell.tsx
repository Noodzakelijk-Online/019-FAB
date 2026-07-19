import { useEffect, useState, type ReactNode } from "react";
import {
  Activity,
  BookOpenText,
  Bot,
  ChartNoAxesCombined,
  ChevronLeft,
  FileCheck2,
  FileStack,
  LayoutDashboard,
  Menu,
  PlugZap,
  RefreshCw,
  Scale,
  Search,
  Settings2,
  ShieldCheck,
  X,
} from "lucide-react";

const navigation = [
  { id: "control-room", label: "Control room", icon: LayoutDashboard },
  { id: "documents", label: "Documents", icon: FileStack },
  { id: "exceptions", label: "Review queue", icon: FileCheck2 },
  { id: "ledger", label: "Ledger", icon: BookOpenText },
  { id: "reconciliation", label: "Reconciliation", icon: Scale },
  { id: "reports", label: "Reports", icon: ChartNoAxesCombined },
  { id: "connections", label: "Connections", icon: PlugZap },
  { id: "audit", label: "Audit", icon: ShieldCheck },
];

type FabOperatorShellProps = {
  children: ReactNode;
  connected: boolean;
  connectionStatus: string;
  organization: string;
  operatorLabel: string;
  search: string;
  onSearchChange: (value: string) => void;
  onRefresh: () => void;
  refreshing: boolean;
  onOpenCommands: () => void;
};

export function FabOperatorShell({
  children,
  connected,
  connectionStatus,
  organization,
  operatorLabel,
  search,
  onSearchChange,
  onRefresh,
  refreshing,
  onOpenCommands,
}: FabOperatorShellProps) {
  const [navOpen, setNavOpen] = useState(false);
  const [activeSection, setActiveSection] = useState("control-room");

  useEffect(() => {
    if (!("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
      if (visible?.target.id) setActiveSection(visible.target.id);
    }, { rootMargin: "-18% 0px -68%", threshold: [0, 0.15, 0.5] });

    const observed = new Set<HTMLElement>();
    const observeSections = () => {
      navigation.forEach(({ id }) => {
        const section = document.getElementById(id);
        if (section && !observed.has(section)) {
          observed.add(section);
          observer.observe(section);
        }
      });
      if (observed.size === navigation.length) mutationObserver.disconnect();
    };
    const mutationObserver = new MutationObserver(observeSections);
    mutationObserver.observe(document.body, { childList: true, subtree: true });
    observeSections();

    return () => {
      mutationObserver.disconnect();
      observer.disconnect();
    };
  }, []);

  function navigate(sectionId: string) {
    setActiveSection(sectionId);
    document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setNavOpen(false);
  }

  return (
    <div className="fab-operator">
      <aside className={`fab-sidebar ${navOpen ? "is-open" : ""}`} aria-label="FAB navigation">
        <div className="fab-brand">
          <div className="fab-brand-mark"><Bot aria-hidden="true" /></div>
          <div><strong>FAB</strong><span>Bookkeeping OS</span></div>
          <button className="fab-icon-button fab-nav-close" onClick={() => setNavOpen(false)} aria-label="Close navigation" title="Close navigation">
            <ChevronLeft aria-hidden="true" />
          </button>
        </div>
        <nav className="fab-nav">
          <span className="fab-nav-label">Workspace</span>
          {navigation.map(({ id, label, icon: Icon }) => (
            <button key={id} className={activeSection === id ? "is-active" : ""} onClick={() => navigate(id)} aria-current={activeSection === id ? "page" : undefined}>
              <Icon aria-hidden="true" /><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="fab-sidebar-footer">
          <button onClick={() => { setNavOpen(false); onOpenCommands(); }}><Settings2 aria-hidden="true" /><span>Safe commands</span></button>
          <div className="fab-operator-id"><Activity aria-hidden="true" /><span><strong>{operatorLabel}</strong><small>Authenticated operator</small></span></div>
        </div>
      </aside>

      {navOpen && <button className="fab-nav-scrim" onClick={() => setNavOpen(false)} aria-label="Close navigation overlay" />}

      <div className="fab-workspace">
        <header className="fab-topbar">
          <button className="fab-icon-button fab-menu-button" onClick={() => setNavOpen(true)} aria-label="Open navigation" title="Open navigation">
            <Menu aria-hidden="true" />
          </button>
          <div className="fab-organization">
            <span>Organization</span>
            <strong>{organization}</strong>
          </div>
          <div className={`fab-connection-pill tone-${connected ? "good" : "bad"}`}>
            <span className="fab-status-dot" />
            {connected ? "Local API connected" : connectionStatus}
          </div>
          <label className="fab-search">
            <Search aria-hidden="true" />
            <span className="sr-only">Search control center</span>
            <input value={search} onChange={(event) => onSearchChange(event.target.value)} placeholder="Search exceptions, sources, activity" />
            {search && <button type="button" onClick={() => onSearchChange("")} aria-label="Clear search" title="Clear search"><X aria-hidden="true" /></button>}
          </label>
          <button className="fab-icon-button" onClick={onRefresh} disabled={refreshing} aria-label="Refresh control center" title="Refresh control center">
            <RefreshCw className={refreshing ? "is-spinning" : ""} aria-hidden="true" />
          </button>
          <div className="fab-avatar" aria-label={`Signed in as ${operatorLabel}`}>{operatorLabel.slice(0, 2).toUpperCase()}</div>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
