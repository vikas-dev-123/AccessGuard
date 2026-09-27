export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "accessguard.token";

export type Role = "auditor" | "viewer";
export type RiskRating = "High" | "Medium" | "Low" | "Informational";
export const RISK_ORDER: RiskRating[] = ["High", "Medium", "Low", "Informational"];

export interface User {
  username: string;
  full_name: string;
  role: Role;
}

export interface Dataset {
  id: number;
  uploaded_at: string;
  uploaded_by: string;
  systems: string[];
  file_names: Record<string, string>;
  hr_employee_count: number;
  account_counts: Record<string, number>;
}

export interface Review {
  id: number;
  dataset_id: number;
  run_at: string;
  run_by: string;
  as_of_date: string;
  systems: string[];
  total_findings: number;
}

export interface Finding {
  finding_id: string;
  check_code: string;
  check_name: string;
  system: string;
  employee_id: string | null;
  username: string;
  details: string;
  risk_rating: RiskRating;
  detected_at: string;
}

export interface FindingsPage {
  total: number;
  items: Finding[];
}

export interface Summary {
  review_id: number;
  total: number;
  by_risk: Record<RiskRating, number>;
  by_check: Record<string, number>;
  by_system: Record<string, number>;
}

export interface Check {
  code: string;
  name: string;
  criteria: string;
  impact: string;
  recommendation: string;
}

export interface UploadError {
  file: string | null;
  error: string;
}

export interface FindingFilters {
  system?: string;
  check?: string;
  risk_rating?: string;
  search?: string;
}

export class ApiError extends Error {
  status: number;
  errors?: UploadError[];

  constructor(status: number, message: string, errors?: UploadError[]) {
    super(message);
    this.status = status;
    this.errors = errors;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage blocked (private mode etc.): the session just won't survive a reload.
  }
}

let unauthorizedHandler: (() => void) | null = null;

export function onUnauthorized(handler: () => void): void {
  unauthorizedHandler = handler;
}

async function toApiError(res: Response): Promise<ApiError> {
  let detail: unknown;
  try {
    detail = (await res.json()).detail;
  } catch {
    // Body was not JSON.
  }
  if (detail && typeof detail === "object" && !Array.isArray(detail) && "errors" in detail) {
    const d = detail as { message: string; errors: UploadError[] };
    return new ApiError(res.status, d.message, d.errors);
  }
  if (typeof detail === "string") return new ApiError(res.status, detail);
  if (Array.isArray(detail)) {
    return new ApiError(res.status, detail.map((d: { msg?: string }) => d.msg).join("; "));
  }
  return new ApiError(res.status, `Request failed (${res.status})`);
}

async function send(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, `Cannot reach the API at ${API_URL}. Is the backend running?`);
  }
  if (res.status === 401 && token) unauthorizedHandler?.();
  if (!res.ok) throw await toApiError(res);
  return res;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return (await send(path, init)).json() as Promise<T>;
}

async function download(path: string, fallbackName: string): Promise<void> {
  const res = await send(path);
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const name = /filename="?([^";]+)"?/.exec(disposition)?.[1] ?? fallbackName;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; username: string; role: Role }>("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username, password }),
    }),
  me: () => request<User>("/auth/me"),
  upload: (form: FormData) => request<Dataset>("/upload", { method: "POST", body: form }),
  datasets: () => request<Dataset[]>("/datasets"),
  checks: () => request<Check[]>("/checks"),
  reviews: () => request<Review[]>("/reviews"),
  runReview: (body: { dataset_id?: number; as_of_date?: string }) =>
    request<Review>("/reviews/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  summary: (reviewId: number) => request<Summary>(`/reviews/${reviewId}/summary`),
  findings: (reviewId: number, params: FindingFilters & { limit: number; offset: number }) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") query.set(key, String(value));
    }
    return request<FindingsPage>(`/reviews/${reviewId}/findings?${query}`);
  },
  downloadReport: (reviewId: number, kind: "excel" | "pdf") =>
    download(
      `/reviews/${reviewId}/report/${kind}`,
      `accessguard-review-${reviewId}.${kind === "excel" ? "xlsx" : "pdf"}`,
    ),
};
