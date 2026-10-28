export type ApiErrorBody = { code: string; params: Record<string, unknown> };

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiErrorBody,
  ) {
    super(body.code);
  }
}

let csrfToken: string | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

export function getCsrfToken() {
  return csrfToken;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (csrfToken && init.method && init.method !== "GET") {
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    let body: ApiErrorBody = { code: "SERVICE_BUSY", params: {} };
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      // Keep the stable error shape when a proxy returns a non-JSON response.
    }
    throw new ApiError(response.status, body);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function uploadFile(file: File, onProgress?: (value: number) => void) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/api/v1/documents", {
    method: "POST",
    body,
    credentials: "include",
    headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
  });
  if (!response.ok) {
    const body = (await response.json()) as ApiErrorBody;
    throw new ApiError(response.status, body);
  }
  onProgress?.(100);
  return (await response.json()) as { id: string; name: string; status: string };
}
