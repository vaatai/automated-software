const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(body || res.statusText, res.status);
  }
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v != null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

// ── Monitoring ────────────────────────────────────────────
export const monitoring = {
  overview: () => request<OverviewData>("/api/monitoring/overview"),

  active: (p?: ListParams & { website_id?: number }) =>
    request<PaginatedRegistrations>(`/api/monitoring/active${qs({ ...p })}`),

  failed: (p?: ListParams & { website_id?: number; search?: string }) =>
    request<PaginatedRegistrations>(`/api/monitoring/failed${qs({ ...p })}`),

  successMetrics: (p?: { website_id?: number; days?: number }) =>
    request<SuccessMetricsData>(`/api/monitoring/success-metrics${qs({ ...p })}`),

  otpStatus: (p?: { website_id?: number }) =>
    request<OTPStatusData>(`/api/monitoring/otp-status${qs({ ...p })}`),

  dailyUsage: (p?: { website_id?: number; days?: number }) =>
    request<DailyUsageData>(`/api/monitoring/daily-usage${qs({ ...p })}`),

  workers: () => request<WorkerStatusData>("/api/monitoring/workers"),
  queues: () => request<Record<string, number>>("/api/monitoring/queues"),

  logs: (p?: LogParams) =>
    request<PaginatedLogs>(`/api/monitoring/logs${qs({ ...p })}`),

  timeline: (id: number) =>
    request<TimelineData>(`/api/monitoring/registrations/${id}/timeline`),

  screenshots: (p?: ListParams & { website_id?: number }) =>
    request<PaginatedScreenshots>(`/api/monitoring/screenshots${qs({ ...p })}`),

  screenshotFile: (id: number) => `${API_BASE}/api/monitoring/screenshots/${id}`,

  hourlyMetrics: (p?: { website_id?: number; hours?: number }) =>
    request<HourlyMetric[]>(`/api/monitoring/metrics/hourly${qs({ ...p })}`),

  weeklyMetrics: (p?: { website_id?: number; weeks?: number }) =>
    request<WeeklyMetric[]>(`/api/monitoring/metrics/weekly${qs({ ...p })}`),

  rankings: (p?: { days?: number }) =>
    request<RankingItem[]>(`/api/monitoring/metrics/rankings${qs({ ...p })}`),
};

// ── Websites ──────────────────────────────────────────────
export const websites = {
  list: (p?: ListParams & { status?: string; search?: string }) =>
    request<PaginatedWebsites>(`/api/websites/${qs({ ...p })}`),

  get: (id: number) => request<Website>(`/api/websites/${id}`),

  create: (data: WebsiteCreatePayload) =>
    request<Website>("/api/websites/", { method: "POST", body: JSON.stringify(data) }),

  update: (id: number, data: Partial<WebsiteCreatePayload>) =>
    request<Website>(`/api/websites/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  delete: (id: number) =>
    request<void>(`/api/websites/${id}`, { method: "DELETE" }),
};

// ── Registrations ─────────────────────────────────────────
export const registrations = {
  create: (data: { website_id: number; count?: number; priority?: string; custom_data?: Record<string, unknown> }) =>
    request<unknown>("/api/registrations/", { method: "POST", body: JSON.stringify(data) }),
};

// ── Tasks ─────────────────────────────────────────────────
export const tasks = {
  get: (id: string) => request<TaskDetail>(`/api/tasks/${id}`),
  cancel: (id: string) => request<unknown>(`/api/tasks/${id}/cancel`, { method: "POST" }),
  queueStats: () => request<QueueStats>("/api/tasks/queue/stats"),
};

// ── Daily Limits ──────────────────────────────────────────
export const limits = {
  stats: () => request<LimitStats[]>("/api/limits/stats"),
  usage: (id: number, days?: number) =>
    request<LimitUsageHistory>(`/api/limits/${id}/usage${qs({ days })}`),
  update: (id: number, data: { max_registrations_per_day: number }) =>
    request<unknown>(`/api/limits/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};

// ── Types ─────────────────────────────────────────────────
export interface ListParams { limit?: number; offset?: number }
export interface LogParams extends ListParams {
  registration_id?: number; website_id?: number; level?: string;
  step?: string; search?: string; date_from?: string; date_to?: string;
}

export interface OverviewData {
  total_registrations: number; completed: number; failed: number;
  in_progress: number; pending: number; cancelled: number;
  daily_limit_reached: number; success_rate_pct: number;
  active_websites: number; active_proxies: number;
}

export interface RegistrationItem {
  id: number; website_id: number; status: string;
  error_message?: string | null; screenshot_path?: string | null;
  created_at?: string | null; updated_at?: string | null;
  celery_task_id?: string | null;
}

export interface PaginatedRegistrations { total: number; items: RegistrationItem[] }

export interface SuccessMetricsData {
  period_days: number; overall_success_rate_pct: number;
  total_success: number; total_failure: number;
  daily: { date: string; total: number; success: number; failure: number; success_rate_pct: number }[];
}

export interface OTPStatusData {
  total_registrations: number;
  email_otp_verified: number; mobile_otp_verified: number;
  email_otp_pending: number; mobile_otp_pending: number;
  email_verification_rate_pct: number; mobile_verification_rate_pct: number;
}

export interface DailyUsageData {
  period_days: number;
  items: {
    date: string; website_id: number; website_name: string;
    daily_limit: number; registration_count: number;
    success_count: number; failure_count: number; utilization_pct: number;
  }[];
}

export interface WorkerInfo {
  name: string; active_tasks: number; reserved_tasks: number;
  total_completed: number; pool_processes: number | null;
  uptime: number | null;
  active_task_details: { id: string; name: string; args: string; time_start: number | null }[];
}
export interface WorkerStatusData { worker_count: number; workers: WorkerInfo[] }

export interface LogItem {
  id: number; registration_id?: number; level: string;
  step: string; message: string; details?: string | null;
  screenshot_path?: string | null; created_at: string;
}
export interface PaginatedLogs { total: number; items: LogItem[] }

export interface TimelineData {
  registration: RegistrationItem;
  timeline: LogItem[];
}

export interface ScreenshotItem {
  registration_id: number; website_id: number; status: string;
  screenshot_path: string; error_message?: string | null; created_at?: string | null;
}
export interface PaginatedScreenshots { total: number; items: ScreenshotItem[] }

export interface HourlyMetric { date: string; hour: number; total: number; success: number; failure: number }
export interface WeeklyMetric { year: number; week: number; total: number; success: number; failure: number }
export interface RankingItem {
  website_id: number; website_name: string; total: number;
  success: number; failure: number; success_rate_pct: number;
}

export interface Website {
  id: number; name: string; url: string; domain?: string; status: string;
  registration_url?: string; max_registrations_per_day: number;
  form_config?: Record<string, unknown>;
  requires_email_otp?: boolean; requires_mobile_otp?: boolean;
  phone_country?: string;
  created_at?: string; updated_at?: string;
}
export interface PaginatedWebsites { total: number; items: Website[] }
export interface WebsiteCreatePayload {
  name: string;
  url: string;
  form_config: {
    registration_url: string;
    steps: { step_name?: string; fields: Record<string, { selector: string; field_type?: string }>; submit_button?: { selector: string } }[];
  };
  requires_email_otp?: boolean;
  requires_mobile_otp?: boolean;
  max_registrations_per_day?: number;
}

export interface TaskDetail {
  task_id: string; status: string; registration_id?: number;
  website_id?: number; result?: unknown;
}
export interface QueueStats {
  active_workers: number; active_tasks: number;
  reserved_tasks: number; queue_lengths: Record<string, number>;
}

export interface LimitStats {
  website_id: number; website_name: string; daily_limit: number;
  registration_count: number; success_count: number;
  failure_count: number; utilization_pct: number;
}
export interface LimitUsageHistory {
  website_id: number; days: number;
  history: { date: string; registration_count: number; success_count: number; failure_count: number }[];
}
