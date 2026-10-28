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

/**
 * AC-001.3 / DR-02: `shared/api` không được import `features/*`, nên interceptor
 * 401 toàn cục gọi qua một handler mà `features/auth` tự đăng ký lúc khởi động
 * (lưu bản nháp câu hỏi, đặt lại trạng thái phiên) thay vì gọi thẳng vào đó.
 */
let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
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
    if (response.status === 401) unauthorizedHandler?.();
    throw new ApiError(response.status, body);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** DR-04: logout gọi endpoint ngoài tiền tố /api/v1, nên không đi qua apiFetch. */
export async function logout() {
  await fetch("/auth/logout", { method: "POST", credentials: "include" });
}

export type CitationPayload = {
  index?: number;
  document_id: string;
  document_name?: string | null;
  page_start?: number | null;
  page_end?: number | null;
};

export type QuestionStreamEvent =
  | { type: "meta"; answerId: string; readyDocCount: number }
  | { type: "delta"; text: string }
  | { type: "citations"; items: CitationPayload[] }
  | { type: "done"; answerType: string; latencyMs: number; uncited: boolean }
  | { type: "error"; code: string; retryAfterSeconds?: number };

/**
 * Gửi câu hỏi và đọc luồng SSE-over-fetch trả lời theo thời gian thực
 * (T-304 API-09: `meta` → `delta`* → `citations` → `done`, hoặc `error`).
 * DR-04: đây là nơi duy nhất ngoài `sseClient` được gọi `fetch` streaming,
 * vì endpoint vẫn ở `/api/v1` nhưng cần đọc `ReadableStream` thủ công.
 *
 * Không bao giờ `throw`: mọi lỗi (mạng, 401/429/…, đứt kết nối giữa chừng)
 * được chuẩn hoá thành một sự kiện `{type:"error", code}` qua `onEvent`, để
 * T-307 chỉ cần xử lý một nhánh lỗi duy nhất ở phía gọi.
 */
export async function streamQuestion(
  conversationId: string,
  text: string,
  onEvent: (event: QuestionStreamEvent) => void,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(
      `/api/v1/conversations/${conversationId}/questions`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
        },
        body: JSON.stringify({ text }),
      },
    );
  } catch {
    onEvent({ type: "error", code: "ANSWER_NETWORK" });
    return;
  }
  if (!response.ok) {
    let body: ApiErrorBody = { code: "SERVICE_BUSY", params: {} };
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      // Giữ mã lỗi mặc định nếu proxy trả về nội dung không phải JSON.
    }
    if (response.status === 401) unauthorizedHandler?.();
    const retryAfter = body.params?.retry_after_seconds;
    onEvent({
      type: "error",
      code: body.code,
      retryAfterSeconds:
        typeof retryAfter === "number" ? retryAfter : undefined,
    });
    return;
  }
  const reader = response.body?.getReader();
  if (!reader) {
    onEvent({ type: "error", code: "ANSWER_NETWORK" });
    return;
  }
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const item = await reader.read();
      if (item.done) break;
      buffer += decoder.decode(item.value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() ?? "";
      for (const raw of chunks) {
        const eventType = raw.match(/^event: (\w+)/m)?.[1];
        const data = raw.match(/^data: (.+)$/m)?.[1];
        if (!data) continue;
        const parsed = JSON.parse(data) as Record<string, unknown>;
        switch (eventType) {
          case "meta":
            onEvent({
              type: "meta",
              answerId: String(parsed.answer_id ?? ""),
              readyDocCount: Number(parsed.ready_doc_count ?? 0),
            });
            break;
          case "delta":
            onEvent({ type: "delta", text: String(parsed.text ?? "") });
            break;
          case "citations":
            onEvent({
              type: "citations",
              items: (parsed.items as CitationPayload[] | undefined) ?? [],
            });
            break;
          case "done":
            onEvent({
              type: "done",
              answerType: String(parsed.type ?? "answered"),
              latencyMs: Number(parsed.latency_ms ?? 0),
              uncited: Boolean(parsed.uncited),
            });
            break;
          case "error":
            onEvent({
              type: "error",
              code: String(parsed.code ?? "SERVICE_BUSY"),
            });
            break;
          default:
            break;
        }
      }
    }
  } catch {
    // SSE bị đứt giữa chừng (mất mạng) mà không có `event: error` từ máy chủ.
    onEvent({ type: "error", code: "ANSWER_NETWORK" });
  }
}

export type UploadDocumentResult = {
  id: string;
  name: string;
  status: string;
  size_bytes?: number;
  page_count?: number | null;
  uploaded_at?: string;
  expires_at?: string;
};

/**
 * Tải một tệp lên `POST /documents` bằng `XMLHttpRequest` để có tiến trình
 * thật (`upload.onprogress`) và hỗ trợ hủy (`abort()`) — T-109 §5.3/§5.5.
 * Trả về `{ promise, abort }` thay vì chỉ `Promise` để gọi nơi dùng có thể
 * hủy khi người dùng bấm nút Hủy giữa chừng.
 */
export function uploadDocument(
  file: File,
  options: {
    onDuplicate?: "replace" | "keep_both";
    onProgress?: (percent: number) => void;
  } = {},
): { promise: Promise<UploadDocumentResult>; abort: () => void } {
  const xhr = new XMLHttpRequest();
  const query = options.onDuplicate
    ? `?on_duplicate=${options.onDuplicate}`
    : "";
  const promise = new Promise<UploadDocumentResult>((resolve, reject) => {
    xhr.open("POST", `/api/v1/documents${query}`);
    xhr.withCredentials = true;
    if (csrfToken) xhr.setRequestHeader("X-CSRF-Token", csrfToken);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && options.onProgress) {
        options.onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as UploadDocumentResult);
        } catch {
          reject(
            new ApiError(xhr.status, { code: "SERVICE_BUSY", params: {} }),
          );
        }
        return;
      }
      let body: ApiErrorBody = { code: "SERVICE_BUSY", params: {} };
      try {
        body = JSON.parse(xhr.responseText) as ApiErrorBody;
      } catch {
        // Keep the stable error shape when the server returns a non-JSON body.
      }
      reject(new ApiError(xhr.status, body));
    };
    xhr.onerror = () =>
      reject(new ApiError(0, { code: "UPLOAD_NETWORK", params: {} }));
    xhr.onabort = () =>
      reject(new ApiError(0, { code: "UPLOAD_ABORTED", params: {} }));
    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
  return { promise, abort: () => xhr.abort() };
}

/** Yêu cầu máy chủ xử lý lại một tài liệu `failed` (T-205 nút "Thử lại"). */
export async function retryDocument(documentId: string) {
  return apiFetch<{ id: string; status: string }>(
    `/documents/${documentId}/retry`,
    {
      method: "POST",
    },
  );
}

export type DocumentEventPayload = {
  id: string;
  status: string;
  error_code: string | null;
  page_count: number | null;
};

/**
 * Kết nối SSE `GET /documents/events` (T-204/T-205) để cập nhật trạng thái
 * tài liệu theo thời gian thực. DR-04: đây là module duy nhất ngoài
 * `shared/analytics` được phép dựng `EventSource` trực tiếp. Trả về hàm
 * hủy đăng ký — gọi khi unmount để đóng kết nối, tránh rò rỉ.
 */
export function subscribeDocumentEvents(
  onEvent: (payload: DocumentEventPayload) => void,
  onError?: () => void,
): () => void {
  // jsdom (môi trường test) không hiện thực EventSource — bỏ qua an toàn
  // thay vì ném lỗi, để DocumentLibrary vẫn hoạt động được qua GET /documents.
  if (typeof EventSource === "undefined") {
    return () => {};
  }
  const source = new EventSource("/api/v1/documents/events", {
    withCredentials: true,
  });
  source.addEventListener("status", (event) => {
    try {
      const payload = JSON.parse(
        (event as MessageEvent<string>).data,
      ) as DocumentEventPayload;
      onEvent(payload);
    } catch {
      // Bỏ qua bản ghi SSE không hợp lệ — không làm hỏng luồng.
    }
  });
  source.onerror = () => {
    onError?.();
  };
  return () => source.close();
}
