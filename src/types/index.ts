export interface Project {
  id: string;
  name: string;
  base_url: string;
  status: string;
  scans: number;
  health: number;
  bugs: number;
  last_scan: string | null;
  created_at: string;
}

export interface AuthSession {
  id: string;
  url: string;
  status: "open" | "completed" | "cancelled" | "expired";
}

export interface AuthProfile {
  id: string;
  url: string;
  domain: string;
  created_at: string;
}

export interface Scan {
  id: string;
  project_id: string | null;
  url: string;
  status: string;
  branch: string | null;
  auth_profile_id: string | null;
  browser: string;
  viewport: string;
  health_score: number | null;
  pages_discovered: number;
  nodes_discovered: number;
  edges_discovered: number;
  bugs_count: number;
  duration_seconds: number | null;
  ai_summary: string | null;
  error_message: string | null;
  progress: number;
  current_phase: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface Bug {
  id: string;
  scan_id: string;
  node_id: string | null;
  severity: "critical" | "high" | "medium" | "low";
  status: string;
  title: string;
  component: string;
  description: string;
  selector: string | null;
  page_url: string | null;
  ai_explanation: string | null;
  fix_suggestion: string | null;
  created_at: string;
  screenshot_url: string | null;
}

export interface ScanLog {
  id: string;
  level: string;
  message: string;
  source: string;
  created_at: string;
}

export interface Screenshot {
  id: string;
  page_url: string;
  viewport: string;
  label: string | null;
  url: string;
  created_at: string;
}

export interface ScanNode {
  id: string;
  url: string;
  label: string;
  parent_node_id: string | null;
  discovered_via: { selector: string; text: string; kind: string } | null;
  lcp_ms: number | null;
  cls: number | null;
  ttfb_ms: number | null;
  load_time_ms: number | null;
  created_at: string;
}

export interface ScanDetail extends Scan {
  logs: ScanLog[];
  screenshots: Screenshot[];
  bugs: Bug[];
  nodes: ScanNode[];
}

export interface DashboardData {
  stats: {
    total_scans: number;
    total_bugs: number;
    avg_health: number;
    hours_saved: number;
  };
  bug_trends: Array<{ date: string; critical: number; high: number; medium: number; low: number }>;
  scan_frequency: Array<{ day: string; scans: number }>;
  recent_scans: Array<{
    id: string;
    url: string;
    score: number;
    bugs: number;
    status: string;
    time: string;
    ago: string;
    branch: string | null;
  }>;
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
  joined: string;
}

export interface UserSettings {
  full_name: string;
  email: string;
  workspace_name: string;
  ai_provider: string;
  notifications_enabled: boolean;
  email_alerts: boolean;
  scan_complete_notify: boolean;
  api_key_hint: string | null;
}
