import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  uploadDocument,
  type UploadDocumentResult,
} from "@shared/api/client";
import { track } from "@shared/analytics/client";
import { validateFiles, type FileReason } from "@shared/validation/files";
import { fileSizeBucket } from "./emptyState";

const MAX_CONCURRENT = 3;
let seq = 0;
const nextLocalId = () => `up-${Date.now()}-${++seq}`;

export type UploadStatus =
  "queued" | "uploading" | "done" | "failed" | "canceled";

export type UploadItem = {
  localId: string;
  file: File;
  status: UploadStatus;
  progress: number;
  documentId?: string;
  errorCode?: string;
};

export type RejectedFile = {
  localId: string;
  fileName: string;
  reasonCode: FileReason;
};
export type DuplicatePrompt = { localId: string; fileName: string };

/**
 * Hàng đợi tải lên phía trình duyệt (T-109 §5.2-§5.5): kiểm tra giới hạn
 * trước khi gửi, tối đa 3 request đồng thời, mỗi tệp một `POST /documents`
 * riêng, xử lý trùng tên (409) và tạm dừng khi bị `429 RATE_LIMITED`.
 */
export function useUploadQueue(params: {
  limits: { max_file_size_bytes: number; max_documents: number };
  usedCount: number;
  onUploaded: (doc: UploadDocumentResult) => void;
}) {
  const { limits, usedCount, onUploaded } = params;
  const [items, setItems] = useState<UploadItem[]>([]);
  const [rejected, setRejected] = useState<RejectedFile[]>([]);
  const [duplicatePrompt, setDuplicatePrompt] =
    useState<DuplicatePrompt | null>(null);
  const [pausedUntil, setPausedUntil] = useState<number | null>(null);

  const abortsRef = useRef(new Map<string, () => void>());
  const startedRef = useRef(new Set<string>());
  const onUploadedRef = useRef(onUploaded);
  onUploadedRef.current = onUploaded;

  const updateItem = useCallback(
    (localId: string, patch: Partial<UploadItem>) => {
      setItems((current) =>
        current.map((item) =>
          item.localId === localId ? { ...item, ...patch } : item,
        ),
      );
    },
    [],
  );

  const removeItem = useCallback((localId: string) => {
    startedRef.current.delete(localId);
    abortsRef.current.delete(localId);
    setItems((current) => current.filter((item) => item.localId !== localId));
  }, []);

  const beginUpload = useCallback(
    (item: UploadItem, onDuplicate?: "replace" | "keep_both") => {
      startedRef.current.add(item.localId);
      updateItem(item.localId, {
        status: "uploading",
        progress: 0,
        errorCode: undefined,
      });
      track("document_upload_started", {
        file_size_bucket: fileSizeBucket(item.file.size),
      });
      const { promise, abort } = uploadDocument(item.file, {
        onDuplicate,
        onProgress: (percent) =>
          updateItem(item.localId, { progress: percent }),
      });
      abortsRef.current.set(item.localId, abort);
      promise
        .then((result) => {
          abortsRef.current.delete(item.localId);
          updateItem(item.localId, {
            status: "done",
            progress: 100,
            documentId: result.id,
          });
          onUploadedRef.current(result);
        })
        .catch((error: unknown) => {
          abortsRef.current.delete(item.localId);
          if (!(error instanceof ApiError)) {
            updateItem(item.localId, {
              status: "failed",
              errorCode: "UPLOAD_NETWORK",
            });
            return;
          }
          if (error.status === 409 && error.body.code === "DUPLICATE_NAME") {
            startedRef.current.delete(item.localId);
            setDuplicatePrompt({
              localId: item.localId,
              fileName: item.file.name,
            });
            return;
          }
          if (error.status === 429) {
            const retryAfter = Number(
              error.body.params?.retry_after_seconds ?? 30,
            );
            setPausedUntil(Date.now() + retryAfter * 1000);
            startedRef.current.delete(item.localId);
            updateItem(item.localId, { status: "queued", progress: 0 });
            return;
          }
          if (error.body.code === "UPLOAD_ABORTED") {
            updateItem(item.localId, { status: "canceled" });
            return;
          }
          updateItem(item.localId, {
            status: "failed",
            errorCode: error.body.code || "UPLOAD_NETWORK",
          });
        });
    },
    [updateItem],
  );

  // Bộ chạy hàng đợi: khi có slot trống (< 3 đang uploading) và không bị
  // tạm dừng/không có hộp thoại trùng tên đang mở, bắt đầu các tệp 'queued'.
  useEffect(() => {
    if (pausedUntil !== null) {
      if (Date.now() < pausedUntil) {
        const timer = setTimeout(
          () => setPausedUntil(null),
          pausedUntil - Date.now(),
        );
        return () => clearTimeout(timer);
      }
      setPausedUntil(null);
      return;
    }
    if (duplicatePrompt) return;
    const uploading = items.filter(
      (item) => item.status === "uploading",
    ).length;
    let slots = MAX_CONCURRENT - uploading;
    if (slots <= 0) return;
    for (const item of items) {
      if (slots <= 0) break;
      if (item.status === "queued" && !startedRef.current.has(item.localId)) {
        slots -= 1;
        beginUpload(item);
      }
    }
  }, [items, pausedUntil, duplicatePrompt, beginUpload]);

  const addFiles = useCallback(
    (files: File[]) => {
      const validations = validateFiles(files, limits, usedCount);
      const accepted: UploadItem[] = [];
      const newlyRejected: RejectedFile[] = [];
      for (const validation of validations) {
        if (validation.ok) {
          accepted.push({
            localId: nextLocalId(),
            file: validation.file,
            status: "queued",
            progress: 0,
          });
        } else if (validation.reasonCode) {
          newlyRejected.push({
            localId: nextLocalId(),
            fileName: validation.file.name,
            reasonCode: validation.reasonCode,
          });
          track("document_upload_rejected_client", {
            reason_code: validation.reasonCode,
          });
        }
      }
      if (accepted.length) setItems((current) => [...current, ...accepted]);
      if (newlyRejected.length)
        setRejected((current) => [...current, ...newlyRejected]);
    },
    [limits, usedCount],
  );

  const cancelUpload = useCallback(
    (localId: string) => {
      abortsRef.current.get(localId)?.();
      removeItem(localId);
    },
    [removeItem],
  );

  const retryFailedItem = useCallback((localId: string) => {
    startedRef.current.delete(localId);
    track("retry_clicked", { context: "document_upload" });
    setItems((current) =>
      current.map((item) =>
        item.localId === localId
          ? { ...item, status: "queued", progress: 0, errorCode: undefined }
          : item,
      ),
    );
  }, []);

  const resolveDuplicate = useCallback(
    (mode: "replace" | "keep_both" | "cancel") => {
      const prompt = duplicatePrompt;
      setDuplicatePrompt(null);
      if (!prompt) return;
      if (mode === "cancel") {
        removeItem(prompt.localId);
        return;
      }
      setItems((current) => {
        const item = current.find((entry) => entry.localId === prompt.localId);
        if (item) beginUpload(item, mode);
        return current;
      });
    },
    [duplicatePrompt, removeItem, beginUpload],
  );

  const dismissRejected = useCallback((localId: string) => {
    setRejected((current) =>
      current.filter((entry) => entry.localId !== localId),
    );
  }, []);

  return {
    items,
    rejected,
    duplicatePrompt,
    paused: pausedUntil !== null,
    addFiles,
    cancelUpload,
    removeItem,
    retryFailedItem,
    resolveDuplicate,
    dismissRejected,
  };
}
