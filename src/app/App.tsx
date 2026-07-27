import { useState, useEffect, useCallback } from "react";
import { motion } from "motion/react";
import { useAuthStore } from "@/stores/authStore";
import { useAppStore } from "@/stores/appStore";
import {
  useDashboard, useProjects, useCreateProject, useCreateScan, useScan,
  useTeam, useInviteMember, useSettings, useUpdateSettings, useBug,
  useStartAuthSession, useAuthSessionStatus, useCompleteAuthSession, useCancelAuthSession,
} from "@/hooks/useVisionQA";
import { env } from "@/config/env";
import { ImageWithFallback } from "@/app/components/figma/ImageWithFallback";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line,
} from "recharts";
import {
  Monitor, Smartphone, Tablet, Play, CheckCircle, XCircle, AlertTriangle,
  ChevronRight, Search, Bell, Settings, Users, CreditCard, Plug, Zap, Shield,
  Eye, Code, Download, ExternalLink, Plus, Moon, Sun, LayoutDashboard, FileText,
  FolderOpen, LogOut, ArrowRight, Activity, Clock, Globe, Star, Check, RefreshCw,
  Filter, MoreHorizontal, Terminal, Camera, Bug, Sparkles, ChevronLeft, Copy,
  GitBranch, TrendingUp, MessageSquare, Upload, Key, User, Mail, Lock, ChevronDown,
  Trash2, Edit, Gauge, Package, BarChart2, Layers, Link2, Workflow, Diff,
  AlertCircle, Info, Cpu, Menu, X,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

type Screen =
  | "landing" | "login" | "signup"
  | "dashboard" | "new-scan" | "live-scan" | "scan-results" | "bug-details"
  | "figma-comparison" | "projects" | "team" | "integrations" | "billing" | "settings";

interface Bug {
  id: string; severity: "critical" | "high" | "medium" | "low";
  title: string; component: string; description: string;
  aiExplanation: string; fixSuggestion: string; selector: string;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const bugTrendData = [
  { date: "Jul 1", critical: 4, high: 8, medium: 12, low: 6 },
  { date: "Jul 5", critical: 3, high: 9, medium: 10, low: 8 },
  { date: "Jul 10", critical: 5, high: 7, medium: 14, low: 5 },
  { date: "Jul 15", critical: 2, high: 6, medium: 11, low: 9 },
  { date: "Jul 18", critical: 1, high: 5, medium: 9, low: 7 },
  { date: "Jul 21", critical: 2, high: 4, medium: 8, low: 6 },
];

const scanHistoryData = [
  { day: "Mon", scans: 18 }, { day: "Tue", scans: 24 }, { day: "Wed", scans: 31 },
  { day: "Thu", scans: 22 }, { day: "Fri", scans: 29 }, { day: "Sat", scans: 12 },
  { day: "Sun", scans: 9 },
];

const recentScans = [
  { id: "s1", url: "app.stripe.com/dashboard", score: 94, bugs: 3, status: "passed", time: "2m 14s", ago: "4 min ago", branch: "main" },
  { id: "s2", url: "github.com/settings/profile", score: 81, bugs: 11, status: "warning", time: "3m 42s", ago: "17 min ago", branch: "feat/ui-refresh" },
  { id: "s3", url: "vercel.com/new", score: 67, bugs: 24, status: "failed", time: "4m 58s", ago: "1h ago", branch: "main" },
  { id: "s4", url: "linear.app/team/issues", score: 97, bugs: 1, status: "passed", time: "1m 38s", ago: "2h ago", branch: "develop" },
  { id: "s5", url: "notion.so/settings", score: 88, bugs: 7, status: "warning", time: "2m 51s", ago: "3h ago", branch: "main" },
];

const mockBugs: Bug[] = [
  {
    id: "b1", severity: "critical", title: "Contrast ratio below WCAG AA", component: "Button.Primary",
    description: "Text contrast ratio of 2.8:1 fails WCAG 2.1 AA minimum of 4.5:1 on small text.",
    aiExplanation: "The primary button uses #8FA3C4 text on a #4A7FBE background. This combination creates insufficient contrast for users with low vision or in bright ambient lighting conditions.",
    fixSuggestion: `// Change text color to meet AA standard\n.btn-primary {\n  color: #ffffff; /* ratio: 6.2:1 ✓ */\n  background: #4A7FBE;\n}`,
    selector: ".btn-primary",
  },
  {
    id: "b2", severity: "high", title: "Focus ring missing on interactive elements", component: "NavItem",
    description: "Keyboard navigation loses visibility when tabbing through sidebar nav items.",
    aiExplanation: "CSS outline: none removes the browser focus indicator without providing an alternative. This breaks keyboard accessibility and fails WCAG 2.1 SC 2.4.7.",
    fixSuggestion: `/* Restore focus visibility */\n.nav-item:focus-visible {\n  outline: 2px solid var(--color-primary);\n  outline-offset: 2px;\n}`,
    selector: ".nav-item",
  },
  {
    id: "b3", severity: "high", title: "Mobile viewport overflow at 375px", component: "DataTable",
    description: "Table overflows viewport on iPhone SE and similar 375px-wide screens.",
    aiExplanation: "The table has a fixed minimum width of 800px without a responsive wrapper. On mobile devices this causes horizontal scroll and breaks the layout flow.",
    fixSuggestion: `<div className="overflow-x-auto w-full">\n  <table className="min-w-[800px]">...\n</div>`,
    selector: ".data-table",
  },
  {
    id: "b4", severity: "medium", title: "Image missing alt text", component: "UserAvatar",
    description: "24 img elements rendered without alt attributes across the dashboard.",
    aiExplanation: "Images without alt text are inaccessible to screen readers. Even decorative images should have alt=\"\" to signal they can be skipped.",
    fixSuggestion: `// For informative images:\n<img src={user.avatar} alt={user.name + "'s avatar"} />\n// For decorative:\n<img src={decoration} alt="" role="presentation" />`,
    selector: "img:not([alt])",
  },
  {
    id: "b5", severity: "low", title: "Button text truncated at 320px", component: "ActionButton",
    description: "CTA button text clips at very small viewport widths.",
    aiExplanation: "The button has overflow: hidden without text-overflow: ellipsis or min-width protection, causing text to be clipped rather than wrapping or truncating gracefully.",
    fixSuggestion: `.action-btn {\n  white-space: nowrap;\n  text-overflow: ellipsis;\n  overflow: hidden;\n  min-width: 88px;\n}`,
    selector: ".action-btn",
  },
];

const teamMembers = [
  { id: "t1", name: "Alex Chen", email: "alex@acme.io", role: "Admin", avatar: "AC", status: "active", joined: "Jan 2024" },
  { id: "t2", name: "Priya Sharma", email: "priya@acme.io", role: "Engineer", avatar: "PS", status: "active", joined: "Feb 2024" },
  { id: "t3", name: "Jordan Lee", email: "jordan@acme.io", role: "Designer", avatar: "JL", status: "active", joined: "Mar 2024" },
  { id: "t4", name: "Marcus Webb", email: "marcus@acme.io", role: "Engineer", avatar: "MW", status: "invited", joined: "—" },
];

const integrations = [
  { id: "i1", name: "GitHub", desc: "Sync scans with pull requests and branches", icon: GitBranch, connected: true, category: "Source Control" },
  { id: "i2", name: "Linear", desc: "Auto-create issues from detected bugs", icon: Layers, connected: true, category: "Project Management" },
  { id: "i3", name: "Slack", desc: "Get scan results and alerts in Slack", icon: MessageSquare, connected: false, category: "Notifications" },
  { id: "i4", name: "Jira", desc: "Create and track bugs in your Jira board", icon: Bug, connected: false, category: "Project Management" },
  { id: "i5", name: "Figma", desc: "Import design files for visual comparison", icon: Diff, connected: true, category: "Design" },
  { id: "i6", name: "Vercel", desc: "Auto-scan preview deployments", icon: Zap, connected: false, category: "Deployment" },
  { id: "i7", name: "Datadog", desc: "Forward scan metrics to your Datadog dashboard", icon: Activity, connected: false, category: "Observability" },
  { id: "i8", name: "PagerDuty", desc: "Trigger alerts on critical scan failures", icon: AlertCircle, connected: false, category: "Alerting" },
];

const invoices = [
  { id: "INV-2024-07", date: "Jul 1, 2024", amount: "$149.00", status: "paid" },
  { id: "INV-2024-06", date: "Jun 1, 2024", amount: "$149.00", status: "paid" },
  { id: "INV-2024-05", date: "May 1, 2024", amount: "$99.00", status: "paid" },
  { id: "INV-2024-04", date: "Apr 1, 2024", amount: "$99.00", status: "paid" },
];

const projects = [
  { id: "p1", name: "Acme Dashboard", url: "app.acme.io", scans: 142, health: 91, bugs: 8, lastScan: "2h ago", status: "passing" },
  { id: "p2", name: "Marketing Site", url: "acme.io", scans: 87, health: 78, bugs: 19, lastScan: "6h ago", status: "warning" },
  { id: "p3", name: "Admin Panel", url: "admin.acme.io", scans: 63, health: 55, bugs: 34, lastScan: "1d ago", status: "failing" },
  { id: "p4", name: "Checkout Flow", url: "checkout.acme.io", scans: 211, health: 96, bugs: 3, lastScan: "30m ago", status: "passing" },
  { id: "p5", name: "Docs Site", url: "docs.acme.io", scans: 44, health: 88, bugs: 11, lastScan: "4h ago", status: "warning" },
  { id: "p6", name: "Mobile Web", url: "m.acme.io", scans: 29, health: 71, bugs: 22, lastScan: "2d ago", status: "warning" },
];

// ─── Primitive Components ─────────────────────────────────────────────────────

function Badge({ children, variant = "default", className = "" }: { children: React.ReactNode; variant?: "default" | "critical" | "high" | "medium" | "low" | "success" | "warning" | "outline" | "primary"; className?: string }) {
  const cls = {
    default: "bg-secondary text-secondary-foreground",
    critical: "bg-red-500/15 text-red-400 border border-red-500/25",
    high: "bg-orange-500/15 text-orange-400 border border-orange-500/25",
    medium: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/25",
    low: "bg-blue-500/15 text-blue-400 border border-blue-500/25",
    success: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25",
    warning: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/25",
    outline: "border border-border text-muted-foreground",
    primary: "bg-primary/15 text-primary border border-primary/25",
  }[variant];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono font-medium ${cls} ${className}`}>
      {children}
    </span>
  );
}

function Btn({
  children, variant = "primary", size = "md", onClick, className = "", disabled = false, icon,
}: {
  children?: React.ReactNode; variant?: "primary" | "secondary" | "ghost" | "destructive" | "outline";
  size?: "sm" | "md" | "lg"; onClick?: (e?: React.MouseEvent) => void; className?: string; disabled?: boolean;
  icon?: React.ReactNode;
}) {
  const base = "inline-flex items-center gap-2 font-medium transition-all duration-150 cursor-pointer select-none rounded-xl disabled:opacity-50 disabled:cursor-not-allowed";
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2 text-sm", lg: "px-6 py-3 text-base" };
  const variants = {
    primary: "bg-primary text-primary-foreground hover:opacity-90 shadow-sm",
    secondary: "bg-secondary text-secondary-foreground hover:bg-muted border border-border",
    ghost: "text-muted-foreground hover:text-foreground hover:bg-secondary",
    destructive: "bg-destructive/10 text-destructive hover:bg-destructive/20 border border-destructive/25",
    outline: "border border-border text-foreground hover:bg-secondary",
  };
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} onClick={onClick} disabled={disabled}>
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </button>
  );
}

function Card({ children, className = "", hover = false, onClick }: { children: React.ReactNode; className?: string; hover?: boolean; onClick?: () => void }) {
  return (
    <div className={`bg-card border border-border rounded-2xl ${hover ? "hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all duration-200" : ""} ${className}`} onClick={onClick}>
      {children}
    </div>
  );
}

function Input({
  label, placeholder, type = "text", value, onChange, icon, className = "",
}: {
  label?: string; placeholder?: string; type?: string; value?: string;
  onChange?: (v: string) => void; icon?: React.ReactNode; className?: string;
}) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label && <label className="text-sm font-medium text-foreground">{label}</label>}
      <div className="relative">
        {icon && <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">{icon}</span>}
        <input
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          className={`w-full bg-input-background border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/50 focus:border-primary transition-all ${icon ? "pl-10" : ""}`}
        />
      </div>
    </div>
  );
}

function StatCard({ label, value, delta, icon: Icon, color = "primary" }: {
  label: string; value: string; delta?: string; icon: React.ElementType; color?: string;
}) {
  const colorMap: Record<string, string> = {
    primary: "text-primary bg-primary/10",
    green: "text-emerald-400 bg-emerald-400/10",
    yellow: "text-yellow-400 bg-yellow-400/10",
    red: "text-red-400 bg-red-400/10",
  };
  return (
    <Card className="p-5" hover>
      <div className="flex items-start justify-between mb-4">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className={`p-2 rounded-lg ${colorMap[color] ?? colorMap.primary}`}>
          <Icon size={15} />
        </span>
      </div>
      <div className="flex items-end gap-2">
        <span className="text-2xl font-bold font-['Outfit'] text-foreground">{value}</span>
        {delta && (
          <span className={`text-xs font-mono mb-0.5 ${delta.startsWith("+") ? "text-emerald-400" : "text-red-400"}`}>
            {delta}
          </span>
        )}
      </div>
    </Card>
  );
}

function HealthScore({ score }: { score: number }) {
  const color = score >= 90 ? "#4ade80" : score >= 70 ? "#fbbf24" : "#f87171";
  const r = 52; const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-36 h-36">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r={r} fill="none" stroke="currentColor" strokeWidth="8" className="text-border" />
          <circle cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="8"
            strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 1s ease" }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold font-['Outfit']" style={{ color }}>{score}</span>
          <span className="text-xs text-muted-foreground font-mono">/ 100</span>
        </div>
      </div>
      <span className="text-sm text-muted-foreground">Health Score</span>
    </div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "projects", label: "Projects", icon: FolderOpen },
  { id: "new-scan", label: "New Scan", icon: Plus },
] as const;

const navBottom = [
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "team", label: "Team", icon: Users },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "settings", label: "Settings", icon: Settings },
] as const;

function Sidebar({
  active, onNav, dark, onToggleDark, onLogout,
}: {
  active: Screen; onNav: (s: Screen) => void; dark: boolean; onToggleDark: () => void; onLogout: () => void;
}) {
  const user = useAuthStore((state) => state.user);
  const { data: settings } = useSettings();
  const { data: dashboard } = useDashboard();
  const { setActiveScanId } = useAppStore();
  const sidebarScans = dashboard?.recent_scans ?? recentScans;
  const initials = user?.full_name
    ? user.full_name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
    : "UQ";

  return (
    <aside className="w-60 bg-sidebar border-r border-sidebar-border flex flex-col shrink-0 h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-sidebar-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Eye size={16} className="text-white" />
          </div>
          <div>
            <span className="font-bold text-sm font-['Outfit'] text-sidebar-foreground">VisionQA</span>
            <span className="block text-xs text-muted-foreground font-mono">AI Tester</span>
          </div>
        </div>
      </div>

      {/* Workspace */}
      <div className="px-3 py-3 border-b border-sidebar-border">
        <button className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl hover:bg-sidebar-accent transition-colors text-left">
          <div className="w-6 h-6 rounded-md bg-primary/20 flex items-center justify-center">
            <span className="text-xs font-bold text-primary">A</span>
          </div>
          <span className="text-sm font-medium text-sidebar-foreground flex-1">{settings?.workspace_name ?? "My Workspace"}</span>
          <ChevronDown size={13} className="text-muted-foreground" />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map(({ id, label, icon: Icon }) => {
          const isActive = active === id;
          return (
            <button key={id} onClick={() => onNav(id as Screen)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${isActive
                ? "bg-primary/10 text-primary font-medium"
                : "text-sidebar-foreground hover:bg-sidebar-accent"}`}>
              <Icon size={15} />
              {label}
              {id === "new-scan" && (
                <span className="ml-auto w-5 h-5 rounded-md bg-primary/20 flex items-center justify-center">
                  <Plus size={11} className="text-primary" />
                </span>
              )}
            </button>
          );
        })}

        <div className="pt-3 pb-1">
          <span className="px-3 text-xs font-mono text-muted-foreground uppercase tracking-wider">Recent Scans</span>
        </div>
        {sidebarScans.slice(0, 3).map((s) => (
          <button key={s.id} onClick={() => { setActiveScanId(s.id); onNav("scan-results"); }}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all text-sidebar-foreground hover:bg-sidebar-accent">
            <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${s.status === "passed" ? "bg-emerald-400" : s.status === "warning" ? "bg-yellow-400" : "bg-red-400"}`} />
            <span className="truncate text-xs text-muted-foreground">{s.url.replace(/.*\//g, "").slice(0, 22)}</span>
          </button>
        ))}
      </nav>

      {/* Bottom nav */}
      <div className="px-3 py-3 border-t border-sidebar-border space-y-0.5">
        {navBottom.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => onNav(id as Screen)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${active === id
              ? "bg-primary/10 text-primary font-medium"
              : "text-sidebar-foreground hover:bg-sidebar-accent"}`}>
            <Icon size={15} />
            {label}
          </button>
        ))}

        {/* Theme + User */}
        <div className="flex items-center gap-2 px-3 py-2 mt-1">
          <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
            <span className="text-xs font-semibold text-primary">{initials}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium truncate text-sidebar-foreground">{user?.full_name ?? "User"}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email ?? ""}</p>
          </div>
          <button onClick={onToggleDark}
            className="p-1.5 rounded-lg hover:bg-sidebar-accent text-muted-foreground hover:text-foreground transition-colors">
            {dark ? <Sun size={13} /> : <Moon size={13} />}
          </button>
          <button onClick={onLogout} title="Sign out"
            className="p-1.5 rounded-lg hover:bg-sidebar-accent text-muted-foreground hover:text-foreground transition-colors">
            <LogOut size={13} />
          </button>
        </div>
      </div>
    </aside>
  );
}

// ─── TopBar ───────────────────────────────────────────────────────────────────

function TopBar({ title, subtitle, actions }: {
  title: string; subtitle?: string; actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between px-8 py-5 border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-10">
      <div>
        <h1 className="text-lg font-semibold font-['Outfit']">{title}</h1>
        {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">
        {actions}
        <button className="relative p-2 rounded-xl hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
          <Bell size={16} />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-primary rounded-full" />
        </button>
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <input placeholder="Search..." className="bg-secondary border border-border rounded-xl pl-8 pr-4 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/50 w-48" />
        </div>
      </div>
    </div>
  );
}

// ─── Landing Page ─────────────────────────────────────────────────────────────

function LandingPage({ onNav, dark, onToggleDark }: {
  onNav: (s: Screen) => void; dark: boolean; onToggleDark: () => void;
}) {
  const features = [
    { icon: Cpu, title: "AI-Powered Analysis", desc: "GPT-4 Vision scans your UI for bugs, contrast issues, layout breaks, and accessibility violations in real time." },
    { icon: Diff, title: "Figma Comparison", desc: "Upload your design files and get pixel-level diffs between your Figma mockups and the live implementation." },
    { icon: Globe, title: "Cross-Browser Testing", desc: "Simultaneously test on Chrome, Firefox, Safari, and Edge across desktop, tablet, and mobile viewports." },
    { icon: Zap, title: "CI/CD Integration", desc: "Embed VisionQA in your pull request workflow. Fail the build on critical regressions, auto-comment findings." },
    { icon: Shield, title: "Accessibility Auditing", desc: "Full WCAG 2.1 AA/AAA compliance scanning. Get actionable reports with component-level fix suggestions." },
    { icon: Activity, title: "Real-time Monitoring", desc: "Continuous health scores, trend analytics, and Slack/Linear alerts so you catch regressions before users do." },
  ];

  const steps = [
    { n: "01", title: "Connect Your Project", desc: "Enter a URL or connect your GitHub repo. VisionQA spins up a headless browser and loads your app." },
    { n: "02", title: "AI Scans Your UI", desc: "Our AI engine captures screenshots, runs accessibility checks, compares to your Figma designs, and logs console errors." },
    { n: "03", title: "Review Actionable Results", desc: "Get a health score, prioritized bug list with AI explanations, one-click fix suggestions, and export-ready reports." },
  ];

  const plans = [
    { name: "Starter", price: "$0", period: "forever", desc: "For individuals and open-source projects", features: ["50 scans/month", "1 project", "Chrome only", "7-day history", "Community support"], highlight: false },
    { name: "Pro", price: "$49", period: "/month", desc: "For growing engineering teams", features: ["Unlimited scans", "10 projects", "All browsers + devices", "Figma comparison", "CI/CD integration", "90-day history", "Priority support"], highlight: true },
    { name: "Enterprise", price: "Custom", period: "", desc: "For large organizations", features: ["Everything in Pro", "Unlimited projects", "SSO/SAML", "Custom workflows", "SLA guarantee", "Dedicated success manager", "On-prem option"], highlight: false },
  ];

  return (
    <div className="min-h-screen bg-background overflow-x-hidden">
      {/* Nav */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
              <Eye size={14} className="text-white" />
            </div>
            <span className="font-bold text-sm font-['Outfit']">VisionQA</span>
          </div>
          <nav className="hidden md:flex items-center gap-6">
            {["Features", "How it works", "Pricing", "Docs"].map((l) => (
              <a key={l} href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">{l}</a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <button onClick={onToggleDark} className="p-2 rounded-lg hover:bg-secondary text-muted-foreground">
              {dark ? <Sun size={15} /> : <Moon size={15} />}
            </button>
            <Btn variant="ghost" size="sm" onClick={() => onNav("login")}>Sign in</Btn>
            <Btn size="sm" onClick={() => onNav("signup")}>Get started</Btn>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* Grid pattern */}
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: `linear-gradient(var(--color-foreground) 1px, transparent 1px), linear-gradient(90deg, var(--color-foreground) 1px, transparent 1px)`,
          backgroundSize: "48px 48px",
        }} />
        {/* Glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-primary/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-6xl mx-auto px-6 py-24 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-primary/30 bg-primary/5 text-xs font-mono text-primary mb-8">
            <Sparkles size={11} />
            Powered by GPT-4 Vision & AI agents
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold font-['Outfit'] leading-[1.1] tracking-tight mb-6">
            AI-powered frontend testing<br />
            <span className="bg-gradient-to-r from-primary via-purple-400 to-primary bg-clip-text text-transparent">
              that catches what humans miss
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
            VisionQA autonomously scans your web app for UI bugs, accessibility violations, layout breaks,
            and Figma deviations. Get health scores, AI explanations, and fix suggestions — in under 3 minutes.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Btn size="lg" onClick={() => onNav("signup")} icon={<ArrowRight size={16} />}>
              Start scanning free
            </Btn>
            <Btn size="lg" variant="outline" onClick={() => onNav("dashboard")} icon={<Play size={14} />}>
              See live demo
            </Btn>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">No credit card required · 50 free scans/month</p>

          {/* Hero dashboard mockup */}
          <div className="mt-16 relative">
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-background z-10 pointer-events-none" style={{ top: "60%" }} />
            <Card className="text-left overflow-hidden shadow-2xl shadow-black/20 border-border/50">
              {/* Fake browser chrome */}
              <div className="bg-secondary/50 border-b border-border px-4 py-3 flex items-center gap-3">
                <div className="flex gap-1.5">
                  {["bg-red-400", "bg-yellow-400", "bg-green-400"].map((c, i) => (
                    <div key={i} className={`w-3 h-3 rounded-full ${c} opacity-70`} />
                  ))}
                </div>
                <div className="flex-1 bg-background rounded-lg px-3 py-1 text-xs font-mono text-muted-foreground border border-border">
                  app.acme.io/dashboard — VisionQA Scan #1,247
                </div>
                <Badge variant="primary">● Live</Badge>
              </div>
              <div className="p-6 grid grid-cols-4 gap-4">
                {[
                  { label: "Health Score", val: "91", sub: "↑ 4 pts", color: "text-emerald-400" },
                  { label: "Bugs Found", val: "7", sub: "3 critical", color: "text-red-400" },
                  { label: "Pages Scanned", val: "24", sub: "All passed", color: "text-primary" },
                  { label: "Scan Time", val: "2:34", sub: "↓ 18s faster", color: "text-yellow-400" },
                ].map((s) => (
                  <div key={s.label} className="bg-secondary rounded-xl p-4 border border-border">
                    <p className="text-xs text-muted-foreground mb-1">{s.label}</p>
                    <p className={`text-2xl font-bold font-['Outfit'] ${s.color}`}>{s.val}</p>
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">{s.sub}</p>
                  </div>
                ))}
              </div>
              <div className="px-6 pb-6">
                <ResponsiveContainer width="100%" height={120}>
                  <AreaChart data={bugTrendData}>
                    <defs>
                      <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#5E6AD2" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#5E6AD2" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area type="monotone" dataKey="high" stroke="#5E6AD2" fill="url(#g1)" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-14">
          <span className="text-xs font-mono text-primary uppercase tracking-widest">Features</span>
          <h2 className="text-3xl font-bold font-['Outfit'] mt-2 mb-3">Everything your QA team needs</h2>
          <p className="text-muted-foreground max-w-xl mx-auto">Built for engineering teams who ship fast and need confidence their UI looks right in production.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f) => (
            <Card key={f.title} className="p-6" hover>
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                <f.icon size={18} className="text-primary" />
              </div>
              <h3 className="font-semibold font-['Outfit'] mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-secondary/30 border-y border-border py-24">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-14">
            <span className="text-xs font-mono text-primary uppercase tracking-widest">How it works</span>
            <h2 className="text-3xl font-bold font-['Outfit'] mt-2">From URL to bug report in minutes</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((s, i) => (
              <div key={s.n} className="relative">
                {i < 2 && <div className="hidden md:block absolute top-8 left-full w-full h-px bg-border -translate-x-4" />}
                <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-5">
                  <span className="font-mono font-bold text-primary text-sm">{s.n}</span>
                </div>
                <h3 className="font-semibold font-['Outfit'] mb-2">{s.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="max-w-5xl mx-auto px-6 py-24">
        <div className="text-center mb-14">
          <span className="text-xs font-mono text-primary uppercase tracking-widest">Pricing</span>
          <h2 className="text-3xl font-bold font-['Outfit'] mt-2 mb-3">Simple, transparent pricing</h2>
          <p className="text-muted-foreground">Start free. Scale as your team grows.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((p) => (
            <div key={p.name}
              className={`relative rounded-2xl border p-6 flex flex-col transition-all hover:shadow-lg ${p.highlight
                ? "border-primary bg-primary/5 shadow-lg shadow-primary/10"
                : "border-border bg-card hover:border-border/60"}`}>
              {p.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-primary rounded-full text-xs font-mono text-white">
                  Most Popular
                </div>
              )}
              <div className="mb-6">
                <h3 className="font-bold font-['Outfit'] text-lg">{p.name}</h3>
                <p className="text-xs text-muted-foreground mt-0.5">{p.desc}</p>
              </div>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-extrabold font-['Outfit']">{p.price}</span>
                <span className="text-muted-foreground text-sm">{p.period}</span>
              </div>
              <ul className="space-y-2.5 mb-8 flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex items-center gap-2.5 text-sm">
                    <Check size={13} className={p.highlight ? "text-primary" : "text-emerald-400"} />
                    {f}
                  </li>
                ))}
              </ul>
              <Btn variant={p.highlight ? "primary" : "outline"} onClick={() => onNav("signup")} className="w-full justify-center">
                {p.name === "Enterprise" ? "Contact sales" : "Get started"}
              </Btn>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-10">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center">
              <Eye size={12} className="text-white" />
            </div>
            <span className="font-bold text-sm font-['Outfit']">VisionQA</span>
          </div>
          <p className="text-xs text-muted-foreground font-mono">© 2024 VisionQA, Inc. All rights reserved.</p>
          <div className="flex items-center gap-4">
            {["Privacy", "Terms", "Docs", "Status"].map((l) => (
              <a key={l} href="#" className="text-xs text-muted-foreground hover:text-foreground transition-colors">{l}</a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}

// ─── Auth Page ────────────────────────────────────────────────────────────────

function AuthPage({ mode, onNav, dark, onToggleDark }: {
  mode: "login" | "signup"; onNav: (s: Screen) => void; dark: boolean; onToggleDark: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const { login, register, isLoading, error, clearError } = useAuthStore();
  const isLogin = mode === "login";

  const handleSubmit = async () => {
    clearError();
    try {
      if (isLogin) {
        await login({ email, password });
      } else {
        await register({ email, password, full_name: fullName.trim() });
      }
      onNav("dashboard");
    } catch {
      // Error is stored in auth store
    }
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col w-1/2 bg-secondary border-r border-border p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-[0.04]" style={{
          backgroundImage: `radial-gradient(circle, var(--color-foreground) 1px, transparent 1px)`,
          backgroundSize: "28px 28px",
        }} />
        <div className="absolute bottom-0 left-0 right-0 h-1/2 bg-gradient-to-t from-secondary to-transparent pointer-events-none" />
        <div className="relative">
          <div className="flex items-center gap-2 mb-16">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Eye size={16} className="text-white" />
            </div>
            <span className="font-bold font-['Outfit']">VisionQA</span>
          </div>
          <blockquote className="mt-auto">
            <p className="text-2xl font-bold font-['Outfit'] leading-snug mb-4">
              "VisionQA caught 23 critical bugs before our launch that our manual QA team missed entirely."
            </p>
            <footer className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Sarah Kim</span> · Lead Engineer, Stripe
            </footer>
          </blockquote>
        </div>
        <div className="relative mt-16 space-y-3">
          {recentScans.slice(0, 3).map((s) => (
            <div key={s.id} className="flex items-center gap-3 p-3 bg-card rounded-xl border border-border">
              <div className={`w-2 h-2 rounded-full ${s.status === "passed" ? "bg-emerald-400" : s.status === "warning" ? "bg-yellow-400" : "bg-red-400"}`} />
              <span className="text-xs font-mono text-muted-foreground flex-1">{s.url}</span>
              <Badge variant={s.status === "passed" ? "success" : s.status === "warning" ? "warning" : "critical"}>
                {s.score}
              </Badge>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="absolute top-4 right-4">
          <button onClick={onToggleDark} className="p-2 rounded-lg hover:bg-secondary text-muted-foreground">
            {dark ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-bold font-['Outfit'] mb-1.5">
              {isLogin ? "Welcome back" : "Create your account"}
            </h2>
            <p className="text-sm text-muted-foreground">
              {isLogin ? "Sign in to your VisionQA account" : "Start your free trial — no card required"}
            </p>
          </div>

          {/* OAuth buttons */}
          <div className="space-y-2.5 mb-6">
            <Btn variant="outline" className="w-full justify-center gap-2.5" onClick={() => onNav("dashboard")}>
              <GitBranch size={15} /> Continue with GitHub
            </Btn>
            <Btn variant="outline" className="w-full justify-center gap-2.5" onClick={() => onNav("dashboard")}>
              <Globe size={15} /> Continue with Google
            </Btn>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-background px-3 text-xs text-muted-foreground">or continue with email</span>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/25 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="space-y-4">
            {!isLogin && (
              <Input label="Full name" placeholder="Alex Chen" value={fullName} onChange={setFullName} icon={<User size={14} />} />
            )}
            <Input label="Email address" placeholder="you@company.com" type="email" value={email} onChange={setEmail} icon={<Mail size={14} />} />
            <Input label="Password" placeholder="••••••••" type="password" value={password} onChange={setPassword} icon={<Lock size={14} />} />
            {isLogin && (
              <div className="flex justify-end">
                <a href="#" className="text-xs text-primary hover:underline">Forgot password?</a>
              </div>
            )}
            <Btn className="w-full justify-center" onClick={handleSubmit} size="lg" disabled={isLoading}>
              {isLoading ? "Please wait..." : isLogin ? "Sign in" : "Create account"} {!isLoading && <ArrowRight size={15} />}
            </Btn>
          </div>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            {isLogin ? "Don't have an account?" : "Already have an account?"}{" "}
            <button className="text-primary hover:underline font-medium" onClick={() => onNav(isLogin ? "signup" : "login")}>
              {isLogin ? "Sign up" : "Sign in"}
            </button>
          </p>

          <p className="mt-8 text-center text-xs text-muted-foreground">
            By continuing you agree to our{" "}
            <a href="#" className="text-primary hover:underline">Terms</a> and{" "}
            <a href="#" className="text-primary hover:underline">Privacy Policy</a>
          </p>
        </div>
      </div>
    </div>
  );
}

// Scan icon alias
const Scan_ = Activity;

// ─── Dashboard ────────────────────────────────────────────────────────────────

function Dashboard({ onNav }: { onNav: (s: Screen) => void }) {
  const { data, isLoading } = useDashboard();
  const { setActiveScanId } = useAppStore();
  const { data: settings } = useSettings();

  const bugTrendData = data?.bug_trends?.length ? data.bug_trends : [
    { date: "—", critical: 0, high: 0, medium: 0, low: 0 },
  ];
  const scanHistoryData = data?.scan_frequency?.length ? data.scan_frequency : [
    { day: "Mon", scans: 0 }, { day: "Tue", scans: 0 }, { day: "Wed", scans: 0 },
    { day: "Thu", scans: 0 }, { day: "Fri", scans: 0 }, { day: "Sat", scans: 0 }, { day: "Sun", scans: 0 },
  ];
  const recentScansList = data?.recent_scans ?? [];
  const stats = data?.stats;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-card border border-border rounded-xl p-3 shadow-xl text-xs font-mono">
        <p className="text-muted-foreground mb-1">{label}</p>
        {payload.map((p: any) => (
          <p key={p.dataKey} style={{ color: p.color }}>{p.dataKey}: {p.value}</p>
        ))}
      </div>
    );
  };

  const openScan = (id: string) => {
    setActiveScanId(id);
    onNav("scan-results");
  };

  return (
    <div>
      <TopBar title="Dashboard" subtitle={`${settings?.workspace_name ?? "Workspace"} · ${isLoading ? "Loading..." : "Live data"}`}
        actions={<Btn size="sm" onClick={() => onNav("new-scan")} icon={<Plus size={13} />}>New Scan</Btn>}
      />
      <div className="p-8 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Scans" value={String(stats?.total_scans ?? 0)} icon={Scan_} color="primary" />
          <StatCard label="Bugs Detected" value={String(stats?.total_bugs ?? 0)} icon={Bug} color="red" />
          <StatCard label="Avg Health Score" value={String(stats?.avg_health ?? 0)} icon={Gauge} color="green" />
          <StatCard label="Time Saved" value={`${stats?.hours_saved ?? 0}h`} icon={Clock} color="yellow" />
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Bug trends */}
          <Card className="lg:col-span-2 p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="font-semibold font-['Outfit']">Bug Trends</h3>
                <p className="text-xs text-muted-foreground mt-0.5">Last 21 days</p>
              </div>
              <div className="flex items-center gap-3">
                {[["critical", "#f87171"], ["high", "#fb923c"], ["medium", "#fbbf24"]].map(([k, c]) => (
                  <div key={k} className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full" style={{ background: c }} />
                    <span className="text-xs text-muted-foreground font-mono capitalize">{k}</span>
                  </div>
                ))}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={bugTrendData}>
                <defs>
                  {[["c", "#f87171"], ["h", "#fb923c"], ["m", "#fbbf24"]].map(([id, color]) => (
                    <linearGradient key={id} id={`bug${id}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={color} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }} stroke="var(--color-border)" />
                <YAxis tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }} stroke="var(--color-border)" />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="critical" stroke="#f87171" fill="url(#bugc)" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="high" stroke="#fb923c" fill="url(#bugh)" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="medium" stroke="#fbbf24" fill="url(#bugm)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>

          {/* Scan frequency */}
          <Card className="p-6">
            <h3 className="font-semibold font-['Outfit'] mb-1">Scan Frequency</h3>
            <p className="text-xs text-muted-foreground mb-6">This week</p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={scanHistoryData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }} stroke="var(--color-border)" />
                <YAxis tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }} stroke="var(--color-border)" />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="scans" fill="var(--color-primary)" radius={[4, 4, 0, 0]} opacity={0.85} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* Recent scans table */}
        <Card>
          <div className="flex items-center justify-between px-6 py-4 border-b border-border">
            <h3 className="font-semibold font-['Outfit']">Recent Scans</h3>
            <div className="flex items-center gap-2">
              <Btn variant="ghost" size="sm" icon={<Filter size={13} />}>Filter</Btn>
              <Btn variant="secondary" size="sm" onClick={() => onNav("new-scan")} icon={<Plus size={13} />}>New Scan</Btn>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  {["URL", "Health", "Bugs", "Status", "Duration", "Branch", "When", ""].map((h) => (
                    <th key={h} className="text-left px-6 py-3 text-xs font-mono text-muted-foreground uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(recentScansList.length ? recentScansList : recentScans).map((s) => (
                  <tr key={s.id} className="border-b border-border last:border-0 hover:bg-secondary/30 transition-colors cursor-pointer"
                    onClick={() => openScan(s.id)}>
                    <td className="px-6 py-4">
                      <span className="text-sm font-mono text-foreground">{s.url}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-secondary rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all"
                            style={{
                              width: `${s.score}%`,
                              background: s.score >= 90 ? "#4ade80" : s.score >= 70 ? "#fbbf24" : "#f87171",
                            }} />
                        </div>
                        <span className="text-xs font-mono font-semibold" style={{
                          color: s.score >= 90 ? "#4ade80" : s.score >= 70 ? "#fbbf24" : "#f87171",
                        }}>{s.score}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm font-mono">{s.bugs}</span>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={s.status === "passed" ? "success" : s.status === "warning" ? "warning" : "critical"}>
                        {s.status}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-mono text-muted-foreground">{s.time}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5">
                        <GitBranch size={11} className="text-muted-foreground" />
                        <span className="text-xs font-mono text-muted-foreground">{s.branch}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs text-muted-foreground">{s.ago}</span>
                    </td>
                    <td className="px-6 py-4">
                      <Btn variant="ghost" size="sm" icon={<ChevronRight size={13} />} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── New Scan ─────────────────────────────────────────────────────────────────

function NewScan({ onNav }: { onNav: (s: Screen) => void }) {
  const [url, setUrl] = useState("https://");
  const [browser, setBrowser] = useState("chromium");
  const [device, setDevice] = useState("desktop");
  const [step, setStep] = useState(1);
  const [options, setOptions] = useState({ accessibility: true, figma: false, performance: true, console: true });
  const [fillForms, setFillForms] = useState(false);
  const [scanError, setScanError] = useState("");
  const createScan = useCreateScan();
  const { setActiveScanId } = useAppStore();

  const [needsAuth, setNeedsAuth] = useState(false);
  const [authSessionId, setAuthSessionId] = useState<string | null>(null);
  const [authProfile, setAuthProfile] = useState<{ id: string; domain: string } | null>(null);
  const [authError, setAuthError] = useState("");
  const startAuthSession = useStartAuthSession();
  const completeAuthSession = useCompleteAuthSession();
  const cancelAuthSession = useCancelAuthSession();
  const { data: authSession } = useAuthSessionStatus(authSessionId, !!authSessionId);

  useEffect(() => {
    if (authSession?.status === "expired" || authSession?.status === "cancelled") {
      setAuthSessionId(null);
      setAuthError("The login session timed out. Try recording it again.");
    }
  }, [authSession?.status]);

  const recordLogin = async () => {
    setAuthError("");
    try {
      const session = await startAuthSession.mutateAsync(url);
      setAuthSessionId(session.id);
    } catch {
      setAuthError("Couldn't open a browser window. Check the URL and try again.");
    }
  };

  const finishRecordingLogin = async () => {
    if (!authSessionId) return;
    const sessionId = authSessionId;
    setAuthError("");
    // Stop status polling before complete so we don't race a 404 after the session is removed.
    setAuthSessionId(null);
    try {
      const profile = await completeAuthSession.mutateAsync(sessionId);
      setAuthProfile({ id: profile.id, domain: profile.domain });
    } catch {
      setAuthSessionId(sessionId);
      setAuthError("Couldn't save the login session. Keep the browser open, finish logging in, then try Save again.");
    }
  };

  const cancelRecordingLogin = async () => {
    if (!authSessionId) return;
    try {
      await cancelAuthSession.mutateAsync(authSessionId);
    } catch {
      // best effort
    }
    setAuthSessionId(null);
  };

  const browsers = [
    { id: "chrome", label: "Chrome", version: "125" },
    { id: "firefox", label: "Firefox", version: "126" },
    { id: "safari", label: "Safari", version: "17" },
    { id: "edge", label: "Edge", version: "124" },
  ];
  const devices = [
    { id: "desktop", label: "Desktop", sub: "1440 × 900", icon: Monitor },
    { id: "tablet", label: "Tablet", sub: "768 × 1024", icon: Tablet },
    { id: "mobile", label: "Mobile", sub: "375 × 812", icon: Smartphone },
  ];

  const startScan = async () => {
    setScanError("");
    try {
      const scan = await createScan.mutateAsync({
        url,
        browser: browser === "chrome" ? "chromium" : browser,
        viewport: device,
        branch: "main",
        auth_profile_id: needsAuth && authProfile ? authProfile.id : undefined,
        fill_forms: fillForms,
      });
      setActiveScanId(scan.id);
      onNav("live-scan");
    } catch {
      setScanError("Failed to start scan. Check the URL and try again.");
    }
  };

  return (
    <div>
      <TopBar title="New Scan" subtitle="Configure and launch an AI-powered scan" />
      <div className="p-8 max-w-2xl">
        {scanError && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/25 text-sm text-red-400">{scanError}</div>
        )}

        {/* Steps */}
        <div className="flex items-center gap-2 mb-8">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono font-bold transition-all
                ${step === s ? "bg-primary text-primary-foreground" : step > s ? "bg-emerald-500/20 text-emerald-400" : "bg-secondary text-muted-foreground"}`}>
                {step > s ? <Check size={12} /> : s}
              </div>
              <span className={`text-sm ${step === s ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                {["Target URL", "Browser & Device", "Options"][s - 1]}
              </span>
              {s < 3 && <ChevronRight size={14} className="text-border mx-1" />}
            </div>
          ))}
        </div>

        <Card className="p-6 space-y-6">
          {step === 1 && (
            <div className="space-y-5">
              <Input label="Target URL" placeholder="https://your-app.com/dashboard" value={url} onChange={setUrl} icon={<Globe size={14} />} />
              <div>
                <label className="text-sm font-medium block mb-2">Authentication</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setNeedsAuth(false)}
                    className={`p-3 rounded-xl border text-sm transition-all text-center ${!needsAuth ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground hover:border-primary hover:text-primary"}`}>
                    No login needed
                  </button>
                  <button
                    onClick={() => setNeedsAuth(true)}
                    className={`p-3 rounded-xl border text-sm transition-all text-center ${needsAuth ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground hover:border-primary hover:text-primary"}`}>
                    Requires login
                  </button>
                </div>

                {needsAuth && (
                  <div className="mt-3 p-4 rounded-xl border border-border bg-secondary/30 space-y-3">
                    {authError && (
                      <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/25 text-xs text-red-400">{authError}</div>
                    )}

                    {authProfile ? (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm text-emerald-400">
                          <CheckCircle size={14} />
                          Login session saved for {authProfile.domain}
                        </div>
                        <Btn variant="ghost" size="sm" onClick={() => setAuthProfile(null)}>Re-record</Btn>
                      </div>
                    ) : authSessionId ? (
                      <div className="space-y-3">
                        <p className="text-xs text-muted-foreground">
                          A browser window opened on this machine at <span className="font-mono text-foreground">{url}</span>.
                          Log in there, then click below.
                        </p>
                        <div className="flex gap-2">
                          <Btn size="sm" onClick={finishRecordingLogin} disabled={completeAuthSession.isPending} icon={<Check size={13} />}>
                            {completeAuthSession.isPending ? "Saving..." : "I've logged in — Save Session"}
                          </Btn>
                          <Btn variant="ghost" size="sm" onClick={cancelRecordingLogin}>Cancel</Btn>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <p className="text-xs text-muted-foreground">
                          Opens a real browser window so you can log in yourself. Your credentials are never sent to or stored by VisionQA — only the resulting session is saved, encrypted.
                        </p>
                        <Btn size="sm" variant="secondary" onClick={recordLogin} disabled={startAuthSession.isPending || !url} icon={<Lock size={13} />}>
                          {startAuthSession.isPending ? "Opening browser..." : "Record Login"}
                        </Btn>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Depth</label>
                <div className="grid grid-cols-4 gap-2">
                  {["Single page", "Shallow", "Full crawl", "Custom"].map((d) => (
                    <button key={d} className="p-2.5 rounded-xl border border-border text-xs text-muted-foreground hover:border-primary hover:text-primary transition-all text-center">
                      {d}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-5">
              <div>
                <label className="text-sm font-medium block mb-3">Browser</label>
                <div className="grid grid-cols-2 gap-2">
                  {browsers.map((b) => (
                    <button key={b.id} onClick={() => setBrowser(b.id)}
                      className={`flex items-center gap-3 p-3.5 rounded-xl border transition-all text-left ${browser === b.id ? "border-primary bg-primary/5" : "border-border hover:border-border/60"}`}>
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold font-mono ${browser === b.id ? "bg-primary text-white" : "bg-secondary text-muted-foreground"}`}>
                        {b.label[0]}
                      </div>
                      <div>
                        <p className="text-sm font-medium">{b.label}</p>
                        <p className="text-xs text-muted-foreground font-mono">v{b.version}</p>
                      </div>
                      {browser === b.id && <Check size={14} className="text-primary ml-auto" />}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium block mb-3">Viewport</label>
                <div className="grid grid-cols-3 gap-2">
                  {devices.map((d) => (
                    <button key={d.id} onClick={() => setDevice(d.id)}
                      className={`flex flex-col items-center gap-2 p-4 rounded-xl border transition-all ${device === d.id ? "border-primary bg-primary/5" : "border-border hover:border-border/60"}`}>
                      <d.icon size={20} className={device === d.id ? "text-primary" : "text-muted-foreground"} />
                      <p className={`text-sm font-medium ${device === d.id ? "text-primary" : ""}`}>{d.label}</p>
                      <p className="text-xs text-muted-foreground font-mono">{d.sub}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">Configure which checks to run during the scan.</p>
              {(Object.entries(options) as [keyof typeof options, boolean][]).map(([key, val]) => {
                const labels: Record<string, { label: string; desc: string; icon: React.ElementType }> = {
                  accessibility: { label: "Accessibility (WCAG 2.1)", desc: "Contrast, focus, ARIA, keyboard nav", icon: Shield },
                  figma: { label: "Figma Comparison", desc: "Visual diff against your design file", icon: Diff },
                  performance: { label: "Performance Checks", desc: "LCP, CLS, layout shifts, render time", icon: Zap },
                  console: { label: "Console Monitoring", desc: "Errors, warnings, and network failures", icon: Terminal },
                };
                const { label, desc, icon: Icon } = labels[key];
                return (
                  <div key={key} className={`flex items-center gap-4 p-4 rounded-xl border transition-all cursor-pointer ${val ? "border-primary/40 bg-primary/5" : "border-border"}`}
                    onClick={() => setOptions((o) => ({ ...o, [key]: !o[key] }))}>
                    <Icon size={16} className={val ? "text-primary" : "text-muted-foreground"} />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{label}</p>
                      <p className="text-xs text-muted-foreground">{desc}</p>
                    </div>
                    <div className={`w-9 h-5 rounded-full transition-colors relative ${val ? "bg-primary" : "bg-secondary"}`}>
                      <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${val ? "translate-x-4" : "translate-x-0.5"}`} />
                    </div>
                  </div>
                );
              })}

              <div className={`flex items-center gap-4 p-4 rounded-xl border transition-all cursor-pointer ${fillForms ? "border-yellow-500/40 bg-yellow-500/5" : "border-border"}`}
                onClick={() => setFillForms((v) => !v)}>
                <FileText size={16} className={fillForms ? "text-yellow-500" : "text-muted-foreground"} />
                <div className="flex-1">
                  <p className="text-sm font-medium">Fill & Submit Forms</p>
                  <p className="text-xs text-muted-foreground">
                    Forms are always filled with test data to check validation and layout. With this on, non-destructive
                    submit buttons are also clicked — this creates real records in the target app. Off by default.
                  </p>
                </div>
                <div className={`w-9 h-5 rounded-full transition-colors relative shrink-0 ${fillForms ? "bg-yellow-500" : "bg-secondary"}`}>
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${fillForms ? "translate-x-4" : "translate-x-0.5"}`} />
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <Btn variant="ghost" size="sm" onClick={() => setStep(Math.max(1, step - 1))} disabled={step === 1}
              icon={<ChevronLeft size={13} />}>Back</Btn>
            {step < 3
              ? <Btn size="md" onClick={() => setStep(step + 1)} icon={<ChevronRight size={13} />}>Continue</Btn>
              : <Btn size="md" onClick={startScan} disabled={createScan.isPending || (needsAuth && !authProfile)} icon={<Play size={13} />}>
                  {createScan.isPending ? "Starting..." : needsAuth && !authProfile ? "Record login first" : "Start Scan"}
                </Btn>
            }
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── Live Scan ────────────────────────────────────────────────────────────────

function LiveScan({ onNav }: { onNav: (s: Screen) => void }) {
  const { activeScanId } = useAppStore();
  const { data: scan } = useScan(activeScanId, true);

  const progress = scan?.progress ?? 0;
  const phase = scan?.current_phase ?? "Initializing";
  const logs = (scan?.logs ?? []).map((l) => ({
    time: new Date(l.created_at).toLocaleTimeString(),
    level: l.level,
    msg: l.message,
  }));

  useEffect(() => {
    if (scan?.status === "completed") {
      onNav("scan-results");
    }
  }, [scan?.status, onNav]);

  const phases = ["Launching browser", "Loading page", "Capturing screenshots", "Analyzing DOM", "AI analysis", "Complete"];
  const phaseIndex = phases.findIndex((p) => phase?.toLowerCase().includes(p.split(" ")[0].toLowerCase()));
  const activePhase = phaseIndex >= 0 ? phaseIndex : Math.floor((progress / 100) * phases.length);

  const done = scan?.status === "completed" || scan?.status === "failed";

  return (
    <div>
      <TopBar title="Live Scan" subtitle={`${scan?.url ?? "Scanning..."} · ${scan?.browser ?? "chromium"} · ${scan?.viewport ?? "desktop"}`}
        actions={
          done
            ? <Btn size="sm" onClick={() => onNav("scan-results")} icon={<ChevronRight size={13} />}>View Results</Btn>
            : <Btn variant="destructive" size="sm" icon={<X size={13} />}>Stop Scan</Btn>
        }
      />
      <div className="p-8 space-y-5">
        <Card className="p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className={`w-2 h-2 rounded-full ${done ? "bg-emerald-400" : "bg-primary animate-pulse"}`} />
              <span className="text-sm font-medium">{done ? "Scan complete" : phase}</span>
            </div>
            <span className="text-sm font-mono text-muted-foreground">{Math.round(progress)}%</span>
          </div>
          <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
            <motion.div className="h-full rounded-full bg-gradient-to-r from-primary to-purple-400"
              style={{ width: `${progress}%` }} transition={{ duration: 0.3 }} />
          </div>
          <div className="flex items-center gap-4 mt-4 flex-wrap">
            {phases.map((p, i) => (
              <div key={p} className={`flex items-center gap-1.5 text-xs font-mono ${i < activePhase ? "text-emerald-400" : i === activePhase ? "text-primary" : "text-muted-foreground"}`}>
                {i < activePhase ? <Check size={10} /> : i === activePhase ? <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" /> : <div className="w-1.5 h-1.5 rounded-full bg-border" />}
                <span className="hidden md:inline">{p}</span>
              </div>
            ))}
          </div>
        </Card>

        <div className="grid lg:grid-cols-2 gap-5">
          {/* Browser viewport simulation */}
          <Card className="overflow-hidden">
            <div className="bg-secondary border-b border-border px-4 py-2.5 flex items-center gap-3">
              <div className="flex gap-1.5">
                {["bg-red-400/60", "bg-yellow-400/60", "bg-green-400/60"].map((c, i) => (
                  <div key={i} className={`w-2.5 h-2.5 rounded-full ${c}`} />
                ))}
              </div>
              <div className="flex-1 bg-background rounded-lg px-2 py-0.5 text-xs font-mono text-muted-foreground border border-border truncate">
                https://app.acme.io/dashboard
              </div>
              <Camera size={13} className="text-muted-foreground" />
            </div>
            <div className="relative bg-secondary/20 h-64 overflow-hidden">
              {/* Simulated page layout */}
              <div className="p-4 space-y-3">
                <div className="flex gap-3">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className={`flex-1 h-14 rounded-lg border border-border bg-card animate-pulse`} style={{ animationDelay: `${i * 100}ms` }} />
                  ))}
                </div>
                <div className="h-24 rounded-lg border border-border bg-card animate-pulse" />
                <div className="grid grid-cols-3 gap-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 rounded-lg border border-border bg-card animate-pulse" style={{ animationDelay: `${i * 150}ms` }} />
                  ))}
                </div>
              </div>
              {/* AI scan overlay */}
              {!done && (
                <div className="absolute inset-0 pointer-events-none">
                  <motion.div className="absolute border-2 border-primary/60 rounded-lg bg-primary/5"
                    animate={{ top: ["10%", "40%", "70%", "20%", "60%"], left: ["5%", "30%", "60%", "70%", "20%"], width: ["30%", "40%", "25%", "50%", "35%"], height: ["15%", "20%", "12%", "25%", "18%"] }}
                    transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }} />
                </div>
              )}
              {done && (
                <div className="absolute inset-0 flex items-center justify-center bg-emerald-500/5">
                  <div className="flex items-center gap-2 bg-card border border-emerald-500/30 rounded-xl px-4 py-2.5 shadow-lg">
                    <CheckCircle size={16} className="text-emerald-400" />
                    <span className="text-sm font-medium text-emerald-400">Scan complete</span>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* AI Activity + Console */}
          <div className="space-y-4">
            <Card className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles size={14} className="text-primary" />
                <span className="text-sm font-semibold">AI Activity</span>
              </div>
              <div className="space-y-2">
                {[
                  { label: "Layout analysis", pct: 100, done: true },
                  { label: "Accessibility scan", pct: Math.min(progress * 1.5, 100), done: progress > 66 },
                  { label: "Visual comparison", pct: Math.min((progress - 40) * 2, 100), done: progress > 90 },
                  { label: "Fix suggestions", pct: Math.min((progress - 70) * 3.3, 100), done: progress >= 100 },
                ].map((a) => (
                  <div key={a.label}>
                    <div className="flex justify-between mb-0.5">
                      <span className="text-xs text-muted-foreground">{a.label}</span>
                      {a.done ? <Check size={10} className="text-emerald-400 mt-0.5" /> : <span className="text-xs font-mono text-muted-foreground">{Math.max(0, Math.round(a.pct))}%</span>}
                    </div>
                    <div className="h-1 bg-secondary rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-300 ${a.done ? "bg-emerald-400" : "bg-primary"}`}
                        style={{ width: `${Math.max(0, Math.min(a.pct, 100))}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
                <Terminal size={13} className="text-muted-foreground" />
                <span className="text-sm font-semibold">Console</span>
                <span className="ml-auto text-xs font-mono text-muted-foreground">{logs.length} entries</span>
              </div>
              <div className="h-44 overflow-y-auto p-3 space-y-1 bg-background font-mono text-xs">
                {logs.map((l, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-muted-foreground shrink-0">{l.time}</span>
                    <span className={`shrink-0 ${l.level === "error" ? "text-red-400" : l.level === "warn" ? "text-yellow-400" : "text-emerald-400"}`}>
                      [{l.level.toUpperCase()}]
                    </span>
                    <span className="text-foreground">{l.msg}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>

        {/* Screenshots */}
        <Card className="p-6">
          <h3 className="font-semibold font-['Outfit'] mb-4">Screenshots Captured</h3>
          <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
            {(scan?.screenshots ?? []).map((s) => (
              <a key={s.id} href={s.url} target="_blank" rel="noreferrer"
                className="aspect-video bg-secondary rounded-lg border border-border overflow-hidden relative group cursor-pointer hover:border-primary transition-colors block">
                <ImageWithFallback src={s.url} alt={s.label ?? s.page_url} className="w-full h-full object-cover object-top" />
                <div className="absolute inset-0 bg-primary/0 group-hover:bg-primary/10 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <Eye size={14} className="text-primary" />
                </div>
              </a>
            ))}
            {!done && Array.from({ length: Math.max(0, Math.floor(progress / 7) + 1 - (scan?.screenshots?.length ?? 0)) }).slice(0, 12).map((_, i) => (
              <div key={`pending-${i}`} className="aspect-video bg-secondary rounded-lg border border-border overflow-hidden relative group">
                <div className="w-full h-full flex flex-col gap-1 p-2 opacity-50">
                  <div className="h-1.5 bg-muted-foreground/30 rounded w-full animate-pulse" />
                  <div className="h-1.5 bg-muted-foreground/20 rounded w-3/4 animate-pulse" />
                  <div className="flex-1 bg-muted-foreground/10 rounded animate-pulse" />
                </div>
              </div>
            ))}
            {done && !scan?.screenshots?.length && (
              <p className="text-sm text-muted-foreground col-span-full">No screenshots captured.</p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── Scan Results ─────────────────────────────────────────────────────────────

function ScanResults({ onNav }: { onNav: (s: Screen) => void }) {
  const [selected, setSelected] = useState<string | null>(null);
  const { activeScanId, setActiveBugId } = useAppStore();
  const { data: scan } = useScan(activeScanId, false);
  const bugs = scan?.bugs ?? [];
  const score = scan?.health_score ?? 0;
  const critCount = bugs.filter((b) => b.severity === "critical").length;
  const highCount = bugs.filter((b) => b.severity === "high").length;
  const medLowCount = bugs.length - critCount - highCount;

  const handleExport = async () => {
    if (!activeScanId) return;
    const token = useAuthStore.getState().accessToken;
    const res = await fetch(`${env.apiBaseUrl}/scans/${activeScanId}/export`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    const html = await res.text();
    const blob = new Blob([html], { type: "text/html" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `visionqa-report-${activeScanId}.html`;
    a.click();
  };

  return (
    <div>
      <TopBar title="Scan Results" subtitle={`${scan?.url ?? "Scan"} · ${scan?.completed_at ? new Date(scan.completed_at).toLocaleString() : "—"}`}
        actions={
          <div className="flex gap-2">
            <Btn variant="secondary" size="sm" icon={<Download size={13} />} onClick={handleExport}>Export Report</Btn>
            <Btn size="sm" onClick={() => onNav("new-scan")} icon={<RefreshCw size={13} />}>Re-scan</Btn>
          </div>
        }
      />
      <div className="p-8 space-y-6">
        <div className="grid md:grid-cols-4 gap-5 items-start">
          <Card className="p-6 flex flex-col items-center">
            <HealthScore score={score} />
          </Card>
          <Card className="md:col-span-3 p-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
              {[
                { label: "Total Bugs", val: String(bugs.length), color: "text-foreground" },
                { label: "Critical", val: String(critCount), color: "text-red-400" },
                { label: "High", val: String(highCount), color: "text-orange-400" },
                { label: "Medium / Low", val: String(medLowCount), color: "text-yellow-400" },
              ].map((s) => (
                <div key={s.label}>
                  <p className="text-xs text-muted-foreground font-mono mb-0.5">{s.label}</p>
                  <p className={`text-3xl font-bold font-['Outfit'] ${s.color}`}>{s.val}</p>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{scan?.browser ?? "chromium"}</Badge>
              <Badge variant="outline">{scan?.viewport ?? "desktop"}</Badge>
              <Badge variant="outline">WCAG 2.1 AA</Badge>
              <Badge variant="outline">{scan?.screenshots?.length ?? 0} screenshots</Badge>
              <Badge variant="outline">Duration: {scan?.duration_seconds ? `${Math.floor(scan.duration_seconds / 60)}m ${scan.duration_seconds % 60}s` : "—"}</Badge>
              <Badge variant="outline">{scan?.nodes_discovered ?? scan?.pages_discovered ?? 0} pages</Badge>
              {!!scan?.edges_discovered && <Badge variant="outline">{scan.edges_discovered} interactions explored</Badge>}
            </div>
            <div className="mt-4 p-3 rounded-xl bg-primary/5 border border-primary/20 flex items-start gap-2.5">
              <Sparkles size={14} className="text-primary mt-0.5 shrink-0" />
              <p className="text-sm text-muted-foreground">
                <span className="text-foreground font-medium">AI Summary:</span> {scan?.ai_summary ?? "No AI summary available yet."}
              </p>
            </div>
          </Card>
        </div>

        {/* Pages & performance */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold font-['Outfit']">Pages Discovered</h3>
            <Badge variant="outline">{scan?.nodes?.length ?? 0} pages</Badge>
          </div>
          {scan?.nodes?.length ? (
            <div className="divide-y divide-border">
              {scan.nodes.map((n) => {
                const depth = n.parent_node_id ? 1 : 0;
                const lcpColor = n.lcp_ms == null ? "text-muted-foreground" : n.lcp_ms >= 4000 ? "text-red-400" : n.lcp_ms >= 2500 ? "text-yellow-400" : "text-emerald-400";
                const clsColor = n.cls == null ? "text-muted-foreground" : n.cls >= 0.25 ? "text-red-400" : n.cls >= 0.1 ? "text-yellow-400" : "text-emerald-400";
                const ttfbColor = n.ttfb_ms == null ? "text-muted-foreground" : n.ttfb_ms >= 800 ? "text-yellow-400" : "text-emerald-400";
                return (
                  <div key={n.id} className="flex items-center gap-4 py-2.5" style={{ paddingLeft: depth * 20 }}>
                    {depth > 0 && <span className="text-muted-foreground text-xs">↳</span>}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{n.label}</p>
                      <p className="text-xs text-muted-foreground font-mono truncate">{n.url}</p>
                    </div>
                    <div className="hidden sm:flex items-center gap-4 shrink-0 text-xs font-mono">
                      <span className={lcpColor} title="Largest Contentful Paint">LCP {n.lcp_ms ?? "—"}{n.lcp_ms != null && "ms"}</span>
                      <span className={clsColor} title="Cumulative Layout Shift">CLS {n.cls ?? "—"}</span>
                      <span className={ttfbColor} title="Time to First Byte">TTFB {n.ttfb_ms ?? "—"}{n.ttfb_ms != null && "ms"}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No pages recorded for this scan.</p>
          )}
        </Card>

        {/* Screenshot gallery */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold font-['Outfit']">Screenshots Captured</h3>
            <Badge variant="outline">{scan?.screenshots?.length ?? 0} screenshots</Badge>
          </div>
          {scan?.screenshots?.length ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(
                scan.screenshots.reduce<Record<string, typeof scan.screenshots>>((acc, s) => {
                  (acc[s.page_url] ??= []).push(s);
                  return acc;
                }, {})
              ).map(([pageUrl, shots]) => {
                const primary = shots.find((s) => s.viewport === scan.viewport) ?? shots[0];
                return (
                  <div key={pageUrl} className="rounded-xl border border-border overflow-hidden hover:border-primary transition-colors">
                    <a href={primary.url} target="_blank" rel="noreferrer" className="group block">
                      <div className="aspect-video bg-secondary relative overflow-hidden">
                        <ImageWithFallback src={primary.url} alt={primary.label ?? primary.page_url}
                          className="w-full h-full object-cover object-top" />
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                          <Eye size={16} className="text-white drop-shadow" />
                        </div>
                      </div>
                    </a>
                    <div className="px-3 py-2 bg-card">
                      <p className="text-xs font-medium truncate">{(primary.label ?? "Screenshot").split(" · ")[0]}</p>
                      <p className="text-xs text-muted-foreground truncate font-mono">{pageUrl}</p>
                      {shots.length > 1 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {shots.map((s) => (
                            <a key={s.id} href={s.url} target="_blank" rel="noreferrer"
                              className={`text-xs px-1.5 py-0.5 rounded font-mono border ${s.id === primary.id ? "border-primary text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}>
                              {s.viewport}
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No screenshots captured for this scan.</p>
          )}
        </Card>

        {/* Bug list */}
        <Card>
          <div className="flex items-center justify-between px-6 py-4 border-b border-border">
            <h3 className="font-semibold font-['Outfit']">Bugs Detected</h3>
            <div className="flex items-center gap-2">
              <Btn variant="ghost" size="sm" icon={<Filter size={13} />}>Filter</Btn>
              <select className="text-xs bg-secondary border border-border rounded-lg px-3 py-1.5 text-foreground focus:outline-none">
                <option>All severities</option>
                <option>Critical</option>
                <option>High</option>
              </select>
            </div>
          </div>
          <div className="divide-y divide-border">
            {(bugs.length ? bugs : mockBugs.map((b) => ({
              ...b,
              ai_explanation: b.aiExplanation,
              fix_suggestion: b.fixSuggestion,
            }))).map((bug: any) => (
              <div key={bug.id}
                className={`px-6 py-4 cursor-pointer hover:bg-secondary/30 transition-colors ${selected === bug.id ? "bg-secondary/40" : ""}`}
                onClick={() => setSelected(selected === bug.id ? null : bug.id)}>
                <div className="flex items-start gap-4">
                  <Badge variant={bug.severity}>{bug.severity}</Badge>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-medium">{bug.title}</p>
                      <code className="text-xs font-mono text-muted-foreground bg-secondary px-1.5 py-0.5 rounded-md">{bug.component}</code>
                    </div>
                    <p className="text-xs text-muted-foreground">{bug.description}</p>
                    {selected === bug.id && (
                      <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-4 space-y-3">
                        {bug.screenshot_url && (
                          <a href={bug.screenshot_url} target="_blank" rel="noreferrer"
                            className="block rounded-xl border border-border overflow-hidden hover:border-primary transition-colors max-w-xs">
                            <ImageWithFallback src={bug.screenshot_url} alt={`Screenshot of ${bug.page_url ?? "affected page"}`}
                              className="w-full h-32 object-cover object-top" />
                            <p className="text-xs text-muted-foreground font-mono px-2 py-1.5 truncate">{bug.page_url}</p>
                          </a>
                        )}
                        <div className="p-3 rounded-xl bg-primary/5 border border-primary/15">
                          <div className="flex items-center gap-1.5 mb-1.5">
                            <Sparkles size={12} className="text-primary" />
                            <span className="text-xs font-semibold text-primary">AI Explanation</span>
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed">{bug.ai_explanation ?? bug.aiExplanation}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold mb-1.5 flex items-center gap-1.5">
                            <Code size={12} className="text-muted-foreground" /> Suggested Fix
                          </p>
                          <pre className="text-xs font-mono bg-secondary border border-border rounded-xl p-3 overflow-x-auto text-foreground">
                            {bug.fix_suggestion ?? bug.fixSuggestion}
                          </pre>
                        </div>
                      </motion.div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Btn variant="ghost" size="sm" onClick={(e) => { e?.stopPropagation(); setActiveBugId(bug.id); onNav("bug-details"); }} icon={<ExternalLink size={12} />} />
                    <ChevronDown size={14} className={`text-muted-foreground transition-transform ${selected === bug.id ? "rotate-180" : ""}`} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── Bug Details ──────────────────────────────────────────────────────────────

function BugDetails({ onNav }: { onNav: (s: Screen) => void }) {
  const { activeBugId } = useAppStore();
  const { data: bugApi } = useBug(activeBugId);
  const bug = bugApi ?? mockBugs[0];
  const [tab, setTab] = useState<"overview" | "fix" | "history">("overview");
  const bugScreenshotUrl = (bug as any).screenshot_url as string | undefined;

  return (
    <div>
      <TopBar title="Bug Details"
        actions={
          <div className="flex gap-2">
            <Btn variant="ghost" size="sm" onClick={() => onNav("scan-results")} icon={<ChevronLeft size={13} />}>Back to Results</Btn>
            <Btn variant="secondary" size="sm" icon={<GitBranch size={13} />}>Open in Linear</Btn>
            <Btn size="sm" icon={<Check size={13} />}>Mark Fixed</Btn>
          </div>
        }
      />
      <div className="p-8 max-w-4xl space-y-6">
        {/* Header */}
        <div className="flex items-start gap-4">
          <Badge variant={bug.severity}>{bug.severity}</Badge>
          <div>
            <h2 className="text-xl font-bold font-['Outfit']">{bug.title}</h2>
            <div className="flex items-center gap-3 mt-1.5">
              <code className="text-xs font-mono text-muted-foreground">{bug.selector ?? "—"}</code>
              <span className="text-muted-foreground">·</span>
              <code className="text-xs font-mono text-muted-foreground">{bug.component}</code>
              <span className="text-muted-foreground">·</span>
              <span className="text-xs text-muted-foreground">{"created_at" in bug ? new Date((bug as any).created_at).toLocaleDateString() : "Recent"}</span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border">
          {(["overview", "fix", "history"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${tab === t ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
              {t}
            </button>
          ))}
        </div>

        {tab === "overview" && (
          <div className="grid md:grid-cols-2 gap-5">
            {/* Screenshot */}
            <Card className="overflow-hidden">
              <div className="bg-secondary px-4 py-2.5 border-b border-border flex items-center justify-between">
                <span className="text-xs font-mono text-muted-foreground">Screenshot · 1440px</span>
                <Camera size={12} className="text-muted-foreground" />
              </div>
              <div className="bg-background h-52 relative overflow-hidden flex items-center justify-center">
                {bugScreenshotUrl ? (
                  <a href={bugScreenshotUrl} target="_blank" rel="noreferrer" className="block w-full h-full">
                    <ImageWithFallback src={bugScreenshotUrl} alt={(bug as any).page_url ?? "Affected page"}
                      className="w-full h-full object-cover object-top" />
                  </a>
                ) : (
                  <div className="w-full p-6 space-y-3">
                    <div className="h-8 bg-secondary rounded-lg w-3/4" />
                    <div className="flex gap-3">
                      <div className="relative">
                        <div className="px-5 py-2.5 rounded-xl bg-blue-500/40 text-xs font-mono text-white/70">
                          Primary Button
                        </div>
                        <div className="absolute inset-0 border-2 border-red-400 rounded-xl animate-pulse" />
                        <div className="absolute -top-5 -right-1 bg-red-400 text-white text-xs px-1.5 py-0.5 rounded font-mono">
                          2.8:1
                        </div>
                      </div>
                      <div className="px-5 py-2.5 rounded-xl bg-secondary text-xs font-mono text-muted-foreground">
                        Secondary
                      </div>
                    </div>
                    <div className="h-6 bg-secondary rounded w-full" />
                    <div className="h-6 bg-secondary rounded w-2/3" />
                  </div>
                )}
              </div>
            </Card>

            {/* Details */}
            <div className="space-y-4">
              <Card className="p-5">
                <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <AlertTriangle size={14} className="text-red-400" /> Root Cause
                </h4>
                <p className="text-sm text-muted-foreground leading-relaxed">{(bug as any).ai_explanation ?? (bug as any).aiExplanation}</p>
              </Card>
              <Card className="p-5">
                <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Info size={14} className="text-muted-foreground" /> WCAG Criterion
                </h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Criterion</span>
                    <span className="font-mono text-xs">1.4.3 Contrast (Minimum)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Level</span>
                    <Badge variant="critical">AA Fail</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Actual ratio</span>
                    <span className="font-mono text-xs text-red-400">2.8:1</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Required ratio</span>
                    <span className="font-mono text-xs text-emerald-400">4.5:1</span>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        )}

        {tab === "fix" && (
          <div className="space-y-4">
            <Card className="p-5">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold flex items-center gap-2">
                  <Sparkles size={14} className="text-primary" /> AI-Suggested Fix
                </h4>
                <Btn variant="ghost" size="sm" icon={<Copy size={12} />}>Copy</Btn>
              </div>
              <pre className="text-xs font-mono bg-secondary border border-border rounded-xl p-4 overflow-x-auto text-foreground leading-relaxed">
                {(bug as any).fix_suggestion ?? (bug as any).fixSuggestion}
              </pre>
            </Card>
            <Card className="p-5">
              <h4 className="text-sm font-semibold mb-3">Alternative Approaches</h4>
              <div className="space-y-2.5">
                {["Use white text (#ffffff) — 6.2:1 ratio", "Darken background to #2a5fa8 — 5.1:1 ratio", "Add text-shadow for depth without color change"].map((alt) => (
                  <div key={alt} className="flex items-center gap-3 p-3 rounded-xl border border-border hover:border-primary/40 transition-colors cursor-pointer">
                    <Check size={13} className="text-emerald-400 shrink-0" />
                    <span className="text-sm text-muted-foreground">{alt}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {tab === "history" && (
          <Card className="p-5">
            <h4 className="text-sm font-semibold mb-4">Bug History</h4>
            <div className="space-y-3">
              {[
                { date: "Jul 21, 2024", event: "Detected in scan #1247", type: "detected" },
                { date: "Jul 15, 2024", event: "Detected in scan #1201 · Not fixed", type: "detected" },
                { date: "Jul 10, 2024", event: "First detected in scan #1188", type: "detected" },
              ].map((h) => (
                <div key={h.date} className="flex gap-3 items-start">
                  <div className="w-2 h-2 rounded-full bg-red-400 mt-1.5 shrink-0" />
                  <div>
                    <p className="text-sm text-foreground">{h.event}</p>
                    <p className="text-xs text-muted-foreground font-mono">{h.date}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

// ─── Figma Comparison ─────────────────────────────────────────────────────────

function FigmaComparison() {
  const [slider, setSlider] = useState(50);
  const [view, setView] = useState<"side-by-side" | "overlay" | "diff">("side-by-side");
  const diffs = [
    { id: "d1", title: "Button padding mismatch", severity: "medium" as const, x: 25, y: 35 },
    { id: "d2", title: "Font weight off — 400 vs 500", severity: "low" as const, x: 55, y: 22 },
    { id: "d3", title: "Missing drop shadow on card", severity: "high" as const, x: 68, y: 55 },
  ];

  return (
    <div>
      <TopBar title="Figma Comparison" subtitle="app.acme.io/dashboard vs Figma v2.4"
        actions={
          <div className="flex gap-1 p-1 bg-secondary rounded-xl border border-border">
            {(["side-by-side", "overlay", "diff"] as const).map((v) => (
              <button key={v} onClick={() => setView(v)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono capitalize transition-all ${view === v ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                {v.replace("-", " ")}
              </button>
            ))}
          </div>
        }
      />
      <div className="p-8 space-y-5">
        {/* Diff summary */}
        <div className="flex gap-4">
          {[
            { label: "Visual differences", val: "3", color: "text-yellow-400" },
            { label: "Pixel accuracy", val: "94.2%", color: "text-emerald-400" },
            { label: "Design version", val: "v2.4", color: "text-primary" },
          ].map((s) => (
            <Card key={s.label} className="px-5 py-3 flex items-center gap-3">
              <span className={`text-xl font-bold font-['Outfit'] ${s.color}`}>{s.val}</span>
              <span className="text-xs text-muted-foreground">{s.label}</span>
            </Card>
          ))}
          <div className="ml-auto flex items-center gap-2">
            <Btn variant="secondary" size="sm" icon={<Upload size={13} />}>Update Figma file</Btn>
          </div>
        </div>

        {/* Comparison viewport */}
        <Card className="overflow-hidden">
          <div className="bg-secondary border-b border-border px-4 py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-primary" /> Figma Design
              </span>
              <span className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-400" /> Live App
              </span>
            </div>
            <span className="text-xs font-mono text-muted-foreground">1440 × 900</span>
          </div>

          {view === "side-by-side" && (
            <div className="grid grid-cols-2 divide-x divide-border">
              {["Design (Figma v2.4)", "Live (app.acme.io)"].map((label, side) => (
                <div key={label} className="relative h-64 overflow-hidden bg-background">
                  <div className="p-5 space-y-3">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="h-6 w-6 rounded-md bg-primary/20" />
                      <div className="h-3 bg-secondary rounded w-24" />
                      <div className="ml-auto flex gap-2">
                        <div className="h-7 w-20 rounded-lg bg-primary/30 border border-primary/30" />
                        <div className="h-7 w-16 rounded-lg bg-secondary border border-border" />
                      </div>
                    </div>
                    <div className="grid grid-cols-4 gap-2">
                      {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="h-12 rounded-lg border border-border bg-secondary" />
                      ))}
                    </div>
                    <div className="h-28 rounded-xl border border-border bg-secondary" />
                  </div>
                  {/* Diff markers */}
                  {side === 1 && diffs.map((d) => (
                    <div key={d.id} className="absolute" style={{ left: `${d.x}%`, top: `${d.y}%` }}>
                      <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center text-white cursor-pointer
                        ${d.severity === "high" ? "bg-orange-400 border-orange-300" : d.severity === "medium" ? "bg-yellow-400 border-yellow-300" : "bg-blue-400 border-blue-300"}`}>
                        <span className="text-[9px] font-bold">{diffs.indexOf(d) + 1}</span>
                      </div>
                    </div>
                  ))}
                  <div className="absolute bottom-2 left-2">
                    <Badge variant={side === 0 ? "primary" : "success"}>{label}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}

          {view === "overlay" && (
            <div className="relative h-64 overflow-hidden bg-background">
              <div className="absolute inset-0 p-5 space-y-3">
                <div className="h-6 bg-secondary rounded w-24" />
                <div className="grid grid-cols-4 gap-2">
                  {[1, 2, 3, 4].map((i) => <div key={i} className="h-12 rounded-lg border border-border bg-secondary" />)}
                </div>
                <div className="h-28 rounded-xl border border-border bg-secondary" />
              </div>
              <div className="absolute inset-0" style={{ clipPath: `inset(0 ${100 - slider}% 0 0)` }}>
                <div className="w-full h-full bg-primary/5 p-5 space-y-3">
                  <div className="h-6 bg-primary/20 rounded w-24" />
                  <div className="grid grid-cols-4 gap-2">
                    {[1, 2, 3, 4].map((i) => <div key={i} className="h-12 rounded-lg border border-primary/30 bg-primary/10" />)}
                  </div>
                  <div className="h-28 rounded-xl border border-primary/30 bg-primary/10" />
                </div>
              </div>
              <div className="absolute top-0 bottom-0 w-0.5 bg-primary cursor-ew-resize z-10 flex items-center justify-center"
                style={{ left: `${slider}%` }}>
                <div className="w-5 h-5 rounded-full bg-primary border-2 border-white shadow-lg" />
              </div>
              <input type="range" min={0} max={100} value={slider} onChange={(e) => setSlider(Number(e.target.value))}
                className="absolute inset-0 w-full opacity-0 cursor-ew-resize z-20" />
            </div>
          )}

          {view === "diff" && (
            <div className="relative h-64 bg-background overflow-hidden">
              <div className="p-5 space-y-3 opacity-20">
                <div className="h-6 bg-secondary rounded w-24" />
                <div className="grid grid-cols-4 gap-2">
                  {[1, 2, 3, 4].map((i) => <div key={i} className="h-12 rounded-lg border border-border bg-secondary" />)}
                </div>
              </div>
              {diffs.map((d) => (
                <div key={d.id} className="absolute" style={{ left: `${d.x - 4}%`, top: `${d.y - 3}%` }}>
                  <div className={`px-2 py-1 rounded-lg border text-xs font-mono backdrop-blur-sm
                    ${d.severity === "high" ? "bg-orange-500/20 border-orange-500/40 text-orange-400" : d.severity === "medium" ? "bg-yellow-500/20 border-yellow-500/40 text-yellow-400" : "bg-blue-500/20 border-blue-500/40 text-blue-400"}`}>
                    {d.title}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Diff list */}
        <Card>
          <div className="px-6 py-4 border-b border-border">
            <h3 className="font-semibold font-['Outfit']">Visual Differences ({diffs.length})</h3>
          </div>
          <div className="divide-y divide-border">
            {diffs.map((d, i) => (
              <div key={d.id} className="px-6 py-4 flex items-center gap-4 hover:bg-secondary/20 transition-colors cursor-pointer">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white
                  ${d.severity === "high" ? "bg-orange-400" : d.severity === "medium" ? "bg-yellow-400" : "bg-blue-400"}`}>
                  {i + 1}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">{d.title}</p>
                </div>
                <Badge variant={d.severity}>{d.severity}</Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── Projects ─────────────────────────────────────────────────────────────────

function Projects({ onNav }: { onNav: (s: Screen) => void }) {
  const { data: projectList = [], isLoading } = useProjects();
  const createProject = useCreateProject();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://");

  const handleCreate = async () => {
    if (!name.trim() || !baseUrl.trim()) return;
    await createProject.mutateAsync({ name: name.trim(), base_url: baseUrl.trim() });
    setShowForm(false);
    setName("");
    setBaseUrl("https://");
  };

  return (
    <div>
      <TopBar title="Projects" subtitle={`${projectList.length} projects`}
        actions={<Btn size="sm" icon={<Plus size={13} />} onClick={() => setShowForm(true)}>New Project</Btn>}
      />
      <div className="p-8 space-y-5">
        {showForm && (
          <Card className="p-5 space-y-3">
            <Input label="Project name" value={name} onChange={setName} placeholder="Acme Dashboard" />
            <Input label="Base URL" value={baseUrl} onChange={setBaseUrl} placeholder="https://app.example.com" icon={<Globe size={14} />} />
            <div className="flex gap-2">
              <Btn size="sm" onClick={handleCreate} disabled={createProject.isPending}>Create</Btn>
              <Btn variant="ghost" size="sm" onClick={() => setShowForm(false)}>Cancel</Btn>
            </div>
          </Card>
        )}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input placeholder="Search projects..." className="w-full bg-input-background border border-border rounded-xl pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring/50" />
          </div>
          <Btn variant="secondary" size="sm" icon={<Filter size={13} />}>Filter</Btn>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(isLoading ? projects : projectList.map((p) => ({
            id: p.id,
            name: p.name,
            url: p.base_url.replace(/^https?:\/\//, ""),
            scans: p.scans,
            health: p.health,
            bugs: p.bugs,
            lastScan: p.last_scan ?? "—",
            status: p.status,
          }))).map((p) => (
            <Card key={p.id} className="p-5 cursor-pointer" hover onClick={() => onNav("scan-results")}>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold font-['Outfit'] text-sm">{p.name}</h3>
                  <p className="text-xs text-muted-foreground font-mono mt-0.5">{p.url}</p>
                </div>
                <Badge variant={p.status === "passing" ? "success" : p.status === "warning" ? "warning" : "critical"}>
                  {p.status}
                </Badge>
              </div>

              {/* Health meter */}
              <div className="mb-4">
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-muted-foreground">Health Score</span>
                  <span className="text-xs font-mono font-bold" style={{
                    color: p.health >= 90 ? "#4ade80" : p.health >= 70 ? "#fbbf24" : "#f87171",
                  }}>{p.health}</span>
                </div>
                <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{
                    width: `${p.health}%`,
                    background: p.health >= 90 ? "#4ade80" : p.health >= 70 ? "#fbbf24" : "#f87171",
                  }} />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 mb-4">
                {[
                  { label: "Scans", val: p.scans },
                  { label: "Bugs", val: p.bugs },
                  { label: "Last scan", val: p.lastScan },
                ].map((s) => (
                  <div key={s.label}>
                    <p className="text-xs text-muted-foreground">{s.label}</p>
                    <p className="text-sm font-mono font-semibold mt-0.5">{s.val}</p>
                  </div>
                ))}
              </div>

              <div className="flex gap-2">
                <Btn variant="secondary" size="sm" className="flex-1 justify-center" onClick={(e) => { e?.stopPropagation(); onNav("new-scan"); }}>
                  <RefreshCw size={12} /> Scan
                </Btn>
                <Btn variant="ghost" size="sm" icon={<Settings size={12} />} />
              </div>
            </Card>
          ))}

          {/* Add project card */}
          <button className="border border-dashed border-border rounded-2xl p-5 flex flex-col items-center justify-center gap-3 text-muted-foreground hover:text-foreground hover:border-primary/40 transition-all min-h-[200px]"
            onClick={() => setShowForm(true)}>
            <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center">
              <Plus size={18} />
            </div>
            <span className="text-sm font-medium">Add Project</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Team ─────────────────────────────────────────────────────────────────────

function Team() {
  const { data: teamData } = useTeam();
  const inviteMember = useInviteMember();
  const [showInvite, setShowInvite] = useState(false);
  const [inviteName, setInviteName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const members = teamData?.items ?? teamMembers.map((m) => ({
    id: m.id, name: m.name, email: m.email, role: m.role, status: m.status, joined: m.joined,
  }));

  const handleInvite = async () => {
    if (!inviteName.trim() || !inviteEmail.trim()) return;
    await inviteMember.mutateAsync({ name: inviteName.trim(), email: inviteEmail.trim(), role: "Engineer" });
    setShowInvite(false);
    setInviteName("");
    setInviteEmail("");
  };

  return (
    <div>
      <TopBar title="Team" subtitle="Manage members and permissions"
        actions={<Btn size="sm" icon={<Plus size={13} />} onClick={() => setShowInvite(true)}>Invite Member</Btn>}
      />
      <div className="p-8 space-y-5">
        {showInvite && (
          <Card className="p-5 space-y-3">
            <Input label="Name" value={inviteName} onChange={setInviteName} placeholder="Jane Doe" />
            <Input label="Email" value={inviteEmail} onChange={setInviteEmail} placeholder="jane@company.com" icon={<Mail size={14} />} />
            <div className="flex gap-2">
              <Btn size="sm" onClick={handleInvite} disabled={inviteMember.isPending}>Send Invite</Btn>
              <Btn variant="ghost" size="sm" onClick={() => setShowInvite(false)}>Cancel</Btn>
            </div>
          </Card>
        )}
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Total Members", val: String(teamData?.total ?? members.length), icon: Users },
            { label: "Active Now", val: String(teamData?.active ?? 0), icon: Activity },
            { label: "Pending Invites", val: String(teamData?.invited ?? 0), icon: Mail },
          ].map((s) => (
            <Card key={s.label} className="p-4 flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
                <s.icon size={15} className="text-primary" />
              </div>
              <div>
                <p className="text-xl font-bold font-['Outfit']">{s.val}</p>
                <p className="text-xs text-muted-foreground">{s.label}</p>
              </div>
            </Card>
          ))}
        </div>

        <Card>
          <div className="px-6 py-4 border-b border-border flex items-center justify-between">
            <h3 className="font-semibold font-['Outfit']">Members</h3>
            <select className="text-xs bg-secondary border border-border rounded-lg px-3 py-1.5 text-foreground focus:outline-none">
              <option>All roles</option>
              <option>Admin</option>
              <option>Engineer</option>
            </select>
          </div>
          <div className="divide-y divide-border">
            {members.map((m) => (
              <div key={m.id} className="px-6 py-4 flex items-center gap-4 hover:bg-secondary/20 transition-colors">
                <div className="w-9 h-9 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                  <span className="text-xs font-bold text-primary">{m.name.split(" ").map((n: string) => n[0]).join("").slice(0, 2)}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{m.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{m.email}</p>
                </div>
                <Badge variant={m.role === "Admin" ? "primary" : "outline"}>{m.role}</Badge>
                <Badge variant={m.status === "active" ? "success" : "warning"}>{m.status}</Badge>
                <span className="text-xs text-muted-foreground font-mono hidden md:block">Joined {m.joined}</span>
                <Btn variant="ghost" size="sm" icon={<MoreHorizontal size={14} />} />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── Integrations ─────────────────────────────────────────────────────────────

function Integrations() {
  const [connected, setConnected] = useState<Set<string>>(
    new Set(integrations.filter((i) => i.connected).map((i) => i.id))
  );
  const categories = [...new Set(integrations.map((i) => i.category))];

  return (
    <div>
      <TopBar title="Integrations" subtitle="Connect your tools and automate your workflow" />
      <div className="p-8 space-y-8">
        {categories.map((cat) => (
          <div key={cat}>
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">{cat}</h3>
            <div className="grid md:grid-cols-2 gap-4">
              {integrations.filter((i) => i.category === cat).map((intg) => {
                const isConn = connected.has(intg.id);
                return (
                  <Card key={intg.id} className="p-5 flex items-center gap-4" hover>
                    <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 border transition-all
                      ${isConn ? "bg-primary/10 border-primary/30" : "bg-secondary border-border"}`}>
                      <intg.icon size={18} className={isConn ? "text-primary" : "text-muted-foreground"} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold">{intg.name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{intg.desc}</p>
                    </div>
                    <Btn
                      variant={isConn ? "destructive" : "primary"}
                      size="sm"
                      onClick={() => setConnected((s) => {
                        const n = new Set(s);
                        isConn ? n.delete(intg.id) : n.add(intg.id);
                        return n;
                      })}>
                      {isConn ? "Disconnect" : "Connect"}
                    </Btn>
                  </Card>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Billing ──────────────────────────────────────────────────────────────────

function Billing() {
  const [annual, setAnnual] = useState(false);

  return (
    <div>
      <TopBar title="Billing" subtitle="Manage your plan and payment details" />
      <div className="p-8 space-y-6">
        {/* Current plan */}
        <Card className="p-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-bold font-['Outfit'] text-lg">Pro Plan</h3>
                <Badge variant="primary">Active</Badge>
              </div>
              <p className="text-sm text-muted-foreground">Renews August 1, 2024 · $149/month</p>
            </div>
            <Btn variant="outline" size="sm">Manage plan</Btn>
          </div>
          <div className="mt-5 grid grid-cols-3 gap-4">
            {[
              { label: "Scans used", val: "834", max: "Unlimited" },
              { label: "Projects", val: "6", max: "10" },
              { label: "Team members", val: "4", max: "15" },
            ].map((u) => (
              <div key={u.label}>
                <div className="flex justify-between mb-1.5">
                  <span className="text-xs text-muted-foreground">{u.label}</span>
                  <span className="text-xs font-mono text-muted-foreground">{u.val} / {u.max}</span>
                </div>
                <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full" style={{
                    width: u.max === "Unlimited" ? "30%" : `${(parseInt(u.val) / parseInt(u.max)) * 100}%`,
                  }} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Plan selector */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold font-['Outfit']">Change Plan</h3>
            <div className="flex items-center gap-2">
              <span className={`text-sm ${!annual ? "text-foreground" : "text-muted-foreground"}`}>Monthly</span>
              <button onClick={() => setAnnual(!annual)}
                className={`w-10 h-5.5 rounded-full transition-colors relative ${annual ? "bg-primary" : "bg-secondary border border-border"}`}>
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${annual ? "translate-x-5" : "translate-x-0.5"}`} />
              </button>
              <span className={`text-sm ${annual ? "text-foreground" : "text-muted-foreground"}`}>Annual
                <Badge variant="success" className="ml-1.5">-20%</Badge>
              </span>
            </div>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              { name: "Starter", price: annual ? "$0" : "$0", features: ["50 scans/month", "1 project"] },
              { name: "Pro", price: annual ? "$119" : "$149", current: true, features: ["Unlimited scans", "10 projects", "CI/CD"] },
              { name: "Enterprise", price: "Custom", features: ["Unlimited everything", "SSO", "SLA"] },
            ].map((p) => (
              <Card key={p.name} className={`p-5 ${p.current ? "border-primary ring-1 ring-primary/20" : ""}`}>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold font-['Outfit']">{p.name}</h4>
                  {p.current && <Badge variant="primary">Current</Badge>}
                </div>
                <div className="flex items-baseline gap-1 mb-4">
                  <span className="text-2xl font-bold font-['Outfit']">{p.price}</span>
                  {p.price !== "Custom" && <span className="text-xs text-muted-foreground">/mo</span>}
                </div>
                <ul className="space-y-1.5 mb-4">
                  {p.features.map((f) => (
                    <li key={f} className="text-xs text-muted-foreground flex items-center gap-1.5">
                      <Check size={11} className="text-emerald-400" /> {f}
                    </li>
                  ))}
                </ul>
                <Btn variant={p.current ? "secondary" : "outline"} size="sm" className="w-full justify-center">
                  {p.current ? "Current plan" : p.name === "Enterprise" ? "Contact sales" : "Switch"}
                </Btn>
              </Card>
            ))}
          </div>
        </div>

        {/* Invoices */}
        <Card>
          <div className="px-6 py-4 border-b border-border">
            <h3 className="font-semibold font-['Outfit']">Invoice History</h3>
          </div>
          <div className="divide-y divide-border">
            {invoices.map((inv) => (
              <div key={inv.id} className="px-6 py-4 flex items-center gap-4 hover:bg-secondary/20 transition-colors">
                <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center">
                  <FileText size={14} className="text-muted-foreground" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-mono font-medium">{inv.id}</p>
                  <p className="text-xs text-muted-foreground">{inv.date}</p>
                </div>
                <span className="text-sm font-mono font-semibold">{inv.amount}</span>
                <Badge variant="success">{inv.status}</Badge>
                <Btn variant="ghost" size="sm" icon={<Download size={12} />} />
              </div>
            ))}
          </div>
        </Card>

        {/* Payment method */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold font-['Outfit']">Payment Method</h3>
            <Btn variant="secondary" size="sm" icon={<Edit size={12} />}>Update</Btn>
          </div>
          <div className="flex items-center gap-4 p-4 rounded-xl border border-border bg-secondary/30">
            <div className="w-10 h-7 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center">
              <span className="text-xs font-bold text-primary">VISA</span>
            </div>
            <div>
              <p className="text-sm font-medium">Visa ending in 4242</p>
              <p className="text-xs text-muted-foreground font-mono">Expires 12/26</p>
            </div>
            <Badge variant="success" className="ml-auto">Default</Badge>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── Settings ─────────────────────────────────────────────────────────────────

function SettingsPage({ dark, onToggleDark }: { dark: boolean; onToggleDark: () => void }) {
  const [tab, setTab] = useState<"profile" | "notifications" | "api" | "security">("profile");
  const { data: settings } = useSettings();
  const updateSettings = useUpdateSettings();
  const [fullName, setFullName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");

  useEffect(() => {
    if (settings) {
      setFullName(settings.full_name);
      setWorkspaceName(settings.workspace_name);
    }
  }, [settings]);

  const saveProfile = async () => {
    await updateSettings.mutateAsync({ full_name: fullName, workspace_name: workspaceName });
  };
  return (
    <div>
      <TopBar title="Settings" />
      <div className="flex">
        {/* Settings sidebar */}
        <div className="w-48 border-r border-border px-3 py-4 shrink-0 space-y-0.5">
          {(["profile", "notifications", "api", "security"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`w-full px-3 py-2 rounded-xl text-sm text-left capitalize transition-all ${tab === t ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:text-foreground hover:bg-secondary"}`}>
              {t === "api" ? "API Keys" : t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        <div className="flex-1 p-8 max-w-xl space-y-6">
          {tab === "profile" && (
            <>
              <Card className="p-6 space-y-5">
                <h3 className="font-semibold font-['Outfit']">Profile</h3>
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center">
                    <span className="text-xl font-bold text-primary">{fullName.split(" ").map((n) => n[0]).join("").slice(0, 2) || "UQ"}</span>
                  </div>
                  <Btn variant="secondary" size="sm" icon={<Upload size={12} />}>Upload photo</Btn>
                  <Btn variant="ghost" size="sm">Remove</Btn>
                </div>
                <Input label="Full name" value={fullName} onChange={setFullName} placeholder="Alex Chen" />
                <Input label="Email address" value={settings?.email ?? ""} placeholder="you@company.com" type="email" icon={<Mail size={14} />} />
                <Input label="Workspace" value={workspaceName} onChange={setWorkspaceName} placeholder="My Workspace" />
                <Btn onClick={saveProfile} disabled={updateSettings.isPending}>Save changes</Btn>
              </Card>
              <Card className="p-6 space-y-4">
                <h3 className="font-semibold font-['Outfit']">Appearance</h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Dark mode</p>
                    <p className="text-xs text-muted-foreground mt-0.5">Switch between light and dark themes</p>
                  </div>
                  <button onClick={onToggleDark}
                    className={`w-11 h-6 rounded-full transition-colors relative ${dark ? "bg-primary" : "bg-secondary border border-border"}`}>
                    <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${dark ? "translate-x-6" : "translate-x-1"}`} />
                  </button>
                </div>
              </Card>
            </>
          )}

          {tab === "notifications" && (
            <Card className="p-6 space-y-5">
              <h3 className="font-semibold font-['Outfit']">Notification Preferences</h3>
              {[
                { label: "Scan completed", desc: "When any scan finishes" },
                { label: "Critical bugs found", desc: "When critical severity bugs are detected" },
                { label: "Health score drop", desc: "When health score drops more than 10 points" },
                { label: "Weekly digest", desc: "Summary of all activity each Monday" },
                { label: "Team activity", desc: "When teammates run scans or change settings" },
              ].map((n, i) => (
                <div key={n.label} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                  <div>
                    <p className="text-sm font-medium">{n.label}</p>
                    <p className="text-xs text-muted-foreground">{n.desc}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {["Email", "Slack"].map((ch) => (
                      <label key={ch} className="flex items-center gap-1.5 cursor-pointer">
                        <input type="checkbox" defaultChecked={i < 3} className="rounded" />
                        <span className="text-xs text-muted-foreground">{ch}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </Card>
          )}

          {tab === "api" && (
            <div className="space-y-5">
              <Card className="p-6">
                <h3 className="font-semibold font-['Outfit'] mb-4">API Keys</h3>
                <div className="space-y-3 mb-5">
                  {[
                    { name: "Production", key: "vqa_live_sk_1a2b3c4d5e6f7g8h9i0j", created: "Jan 15, 2024", last: "2h ago" },
                    { name: "Development", key: "vqa_test_sk_k1l2m3n4o5p6q7r8s9t0", created: "Mar 3, 2024", last: "4d ago" },
                  ].map((k) => (
                    <div key={k.name} className="p-4 rounded-xl border border-border">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">{k.name}</span>
                        <div className="flex gap-1.5">
                          <Btn variant="ghost" size="sm" icon={<Copy size={12} />} />
                          <Btn variant="ghost" size="sm" icon={<Trash2 size={12} />} />
                        </div>
                      </div>
                      <code className="text-xs font-mono text-muted-foreground bg-secondary px-2 py-1 rounded-lg block mb-2">
                        {k.key.slice(0, 24)}••••••••
                      </code>
                      <div className="flex gap-4 text-xs text-muted-foreground">
                        <span>Created {k.created}</span>
                        <span>Last used {k.last}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <Btn variant="secondary" size="sm" icon={<Plus size={12} />}>Generate new key</Btn>
              </Card>
              <Card className="p-6">
                <h3 className="font-semibold font-['Outfit'] mb-2">Webhooks</h3>
                <p className="text-sm text-muted-foreground mb-4">Receive real-time scan events via HTTP POST to your endpoints.</p>
                <Input label="Webhook URL" placeholder="https://your-app.com/webhooks/visionqa" icon={<Link2 size={14} />} />
                <div className="mt-4">
                  <Btn variant="secondary" size="sm">Add webhook</Btn>
                </div>
              </Card>
            </div>
          )}

          {tab === "security" && (
            <div className="space-y-5">
              <Card className="p-6 space-y-4">
                <h3 className="font-semibold font-['Outfit']">Password</h3>
                <Input label="Current password" type="password" placeholder="••••••••" icon={<Lock size={14} />} />
                <Input label="New password" type="password" placeholder="••••••••" icon={<Lock size={14} />} />
                <Input label="Confirm password" type="password" placeholder="••••••••" icon={<Lock size={14} />} />
                <Btn>Update password</Btn>
              </Card>
              <Card className="p-6 space-y-4">
                <h3 className="font-semibold font-['Outfit']">Two-Factor Authentication</h3>
                <p className="text-sm text-muted-foreground">Add an extra layer of security to your account.</p>
                <div className="flex items-center justify-between p-4 rounded-xl border border-border">
                  <div className="flex items-center gap-3">
                    <Smartphone size={16} className="text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">Authenticator app</p>
                      <p className="text-xs text-muted-foreground">Not enabled</p>
                    </div>
                  </div>
                  <Btn variant="secondary" size="sm">Enable</Btn>
                </div>
              </Card>
              <Card className="p-6 space-y-4">
                <h3 className="font-semibold font-['Outfit'] text-destructive">Danger Zone</h3>
                <div className="p-4 rounded-xl border border-destructive/25 bg-destructive/5">
                  <p className="text-sm font-medium">Delete account</p>
                  <p className="text-xs text-muted-foreground mt-0.5 mb-3">This will permanently delete your account and all scan data.</p>
                  <Btn variant="destructive" size="sm">Delete account</Btn>
                </div>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── App Shell ────────────────────────────────────────────────────────────────

function AppShell({ screen, onNav, dark, onToggleDark, onLogout }: {
  screen: Screen; onNav: (s: Screen) => void; dark: boolean; onToggleDark: () => void; onLogout: () => void;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const renderScreen = () => {
    switch (screen) {
      case "dashboard": return <Dashboard onNav={onNav} />;
      case "new-scan": return <NewScan onNav={onNav} />;
      case "live-scan": return <LiveScan onNav={onNav} />;
      case "scan-results": return <ScanResults onNav={onNav} />;
      case "bug-details": return <BugDetails onNav={onNav} />;
      case "figma-comparison": return <FigmaComparison />;
      case "projects": return <Projects onNav={onNav} />;
      case "team": return <Team />;
      case "integrations": return <Integrations />;
      case "billing": return <Billing />;
      case "settings": return <SettingsPage dark={dark} onToggleDark={onToggleDark} />;
      default: return <Dashboard onNav={onNav} />;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {sidebarOpen && <Sidebar active={screen} onNav={onNav} dark={dark} onToggleDark={onToggleDark} onLogout={onLogout} />}
      <main className="flex-1 overflow-y-auto">
        {renderScreen()}
      </main>
    </div>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

const protectedScreens: Screen[] = [
  "dashboard", "new-scan", "live-scan", "scan-results", "bug-details",
  "figma-comparison", "projects", "team", "integrations", "billing", "settings",
];

export default function App() {
  const [screen, setScreen] = useState<Screen>("landing");
  const [dark, setDark] = useState(true);
  const { isAuthenticated, isLoading, logout } = useAuthStore();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  useEffect(() => {
    if (!isLoading && isAuthenticated && (screen === "landing" || screen === "login" || screen === "signup")) {
      setScreen("dashboard");
    }
    if (!isLoading && !isAuthenticated && protectedScreens.includes(screen)) {
      setScreen("login");
    }
  }, [isAuthenticated, isLoading, screen]);

  const toggleDark = useCallback(() => setDark((d) => !d), []);

  const handleNav = useCallback((s: Screen) => {
    if (protectedScreens.includes(s) && !useAuthStore.getState().isAuthenticated) {
      setScreen("login");
      return;
    }
    setScreen(s);
    window.scrollTo(0, 0);
  }, []);

  const handleLogout = useCallback(async () => {
    await logout();
    setScreen("login");
  }, [logout]);

  if (isLoading && isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-sm text-muted-foreground font-mono">Restoring session...</p>
      </div>
    );
  }

  if (screen === "landing") {
    return <LandingPage onNav={handleNav} dark={dark} onToggleDark={toggleDark} />;
  }
  if (screen === "login" || screen === "signup") {
    return <AuthPage mode={screen} onNav={handleNav} dark={dark} onToggleDark={toggleDark} />;
  }
  return <AppShell screen={screen} onNav={handleNav} dark={dark} onToggleDark={toggleDark} onLogout={handleLogout} />;
}
