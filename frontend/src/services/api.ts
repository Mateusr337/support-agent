import { API_URL } from "../lib/env";
import { clearToken, getToken } from "../lib/authStorage";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

interface ValidationErrorItem {
  msg: string;
}

interface ApiErrorPayload {
  detail?: string | ValidationErrorItem[];
}

export interface ApiRequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (auth) {
    const token = getToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 204) {
    return null as T;
  }

  let payload: ApiErrorPayload | null = null;
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    payload = (await response.json()) as ApiErrorPayload;
  }

  if (!response.ok) {
    if (response.status === 401 && auth) {
      clearToken();
    }

    const detail =
      typeof payload?.detail === "string"
        ? payload.detail
        : Array.isArray(payload?.detail)
          ? payload.detail.map((item) => item.msg).join(", ")
          : undefined;

    throw new ApiError(
      response.status,
      detail ?? response.statusText,
      payload?.detail
    );
  }

  return payload as T;
}
