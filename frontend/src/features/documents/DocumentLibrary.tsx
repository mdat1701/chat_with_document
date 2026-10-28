import { useEffect, useState } from "react";
import { apiFetch, retryDocument, ApiError } from "@shared/api/client";
import { useAppConfig } from "@shared/config";
import { Badge, Banner, Button, EmptyState, Skeleton, useToast } from "@shared/ui";
import { track } from "@shared/analytics/client";
import { messages, type ErrorCode, uiText, formatNumber } from "@shared/i18n/messages.vi";
import "./documents.css";
import { UploadDropzone } from "./UploadDropzone";
import { DeleteConfirmDialog } from "./DeleteConfirmDialog";
import { DuplicateFileDialog } from "./DuplicateFileDialog";
import { useDocuments } from "./useDocuments";
import { useUploadQueue, type UploadItem } from "./useUploadQueue";
import { StatusBadge } from "./StatusBadge";
import { markEmptyStateViewedOnce, resolveEmptyState } from "./emptyState";
import type { DocumentVM } from "./types";

type Props = {
  /** Có kết nối mạng hay không (T-109 §5.8 NE-03) — App.tsx giữ state này. */
  online?: boolean;
};

const RETRYABLE_ERRORS = new Set(["UPLOAD_NETWORK", "INGESTION_FAILED"]);

function errorMessage(code?: string | null): string {
  if (code && code in messages) return messages[code as ErrorCode];
  return messages.SERVICE_BUSY;
}

/**
 * Container của cột trái SCR-02 (T-205 §5 `DocumentPanel`): bộ đếm, dropzone,
 * hàng đợi tải lên cục bộ, danh sách tài liệu thật (hợp nhất SSE), trạng
 * thái trống ES-01..ES-05 (T-208), và hộp xác nhận xóa.
 *
 * Lưu ý phạm vi: liên kết khóa/mở ô câu hỏi (`ChatPanel`) theo `readyCount`
 * (T-205 §5 bước 8) **chưa** nối ở đây — `features/chat` thuộc một phiên
 * làm việc song song khác trong lần triển khai này, nên `hasMessages` dùng
 * giá trị mặc định `false` (xem "Ghi chú triển khai thực tế" trong tài liệu
 * task). ES-01/ES-02/ES-03 (chỉ phụ thuộc danh sách tài liệu) vẫn đúng.
 */
export function DocumentLibrary({ online = true }: Props) {
  const { config } = useAppConfig();
  const { showToast } = useToast();
  const { documents, loading, reload, upsertFromUpload, removeLocal } = useDocuments();
  const used = documents.length;

  const { items, rejected, duplicatePrompt, addFiles, cancelUpload, removeItem, retryFailedItem, resolveDuplicate, dismissRejected } =
    useUploadQueue({
      limits: { max_file_size_bytes: config.max_file_size_bytes, max_documents: config.max_documents },
      usedCount: used,
      onUploaded: (doc) => upsertFromUpload(doc),
    });

  const [pendingDelete, setPendingDelete] = useState<DocumentVM | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [retrying, setRetrying] = useState<Set<string>>(new Set());

  const atQuota = used >= config.max_documents;
  const uploadDisabled = !online || atQuota;
  const uploadDisabledReason = !online
    ? uiText.uploadLockedOffline
    : atQuota
      ? uiText.quotaReached
      : undefined;

  const hasMessages = false; // Xem ghi chú ở đầu file — chưa nối với features/chat trong phiên này.
  const variant = loading ? null : resolveEmptyState(documents, hasMessages);

  useEffect(() => {
    if (variant) markEmptyStateViewedOnce(variant);
  }, [variant]);

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await apiFetch<void>(`/documents/${pendingDelete.id}`, { method: "DELETE" });
      removeLocal(pendingDelete.id);
      showToast({ title: uiText.deletedToast(pendingDelete.name), tone: "success" });
      setPendingDelete(null);
    } catch (error) {
      if (error instanceof ApiError && error.body.code === "DOC_NOT_FOUND") {
        removeLocal(pendingDelete.id);
        setPendingDelete(null);
        void reload();
      }
      // Lỗi khác (mạng…): giữ hộp thoại mở, không xóa khỏi danh sách (T-208 §6).
    } finally {
      setDeleting(false);
    }
  };

  const retry = async (doc: DocumentVM) => {
    track("retry_clicked", { context: "document_processing" });
    setRetrying((current) => new Set(current).add(doc.id));
    try {
      await retryDocument(doc.id);
      await reload();
    } catch {
      // Best-effort — trạng thái thật sẽ đến qua SSE/lần tải lại kế tiếp.
    } finally {
      setRetrying((current) => {
        const next = new Set(current);
        next.delete(doc.id);
        return next;
      });
    }
  };

  return (
    <section aria-label="Thư viện tài liệu" className="documents-panel">
      <div className="documents-panel-header">
        <h2>Tài liệu của bạn</h2>
        <Badge tone={atQuota ? "warning" : "neutral"} data-testid="doc-counter" aria-label={uiText.documentCounter(used, config.max_documents)}>
          {formatNumber(used)}/{formatNumber(config.max_documents)}
        </Badge>
      </div>

      <UploadDropzone
        disabled={uploadDisabled}
        disabledReason={uploadDisabledReason}
        hintText={`PDF có văn bản · tối đa ${Math.round(config.max_file_size_bytes / (1024 * 1024))} MB · ${config.max_pages} trang mỗi tệp`}
        onFilesSelected={addFiles}
      />

      {rejected.length > 0 && (
        <Banner tone="warning" data-testid="rejected-files-notice">
          <strong>{uiText.rejectedFilesTitle}</strong>
          <ul>
            {rejected.map((item) => (
              <li key={item.localId}>
                {item.fileName}: {errorMessage(item.reasonCode)}{" "}
                <button type="button" onClick={() => dismissRejected(item.localId)} aria-label="Đóng thông báo">
                  ×
                </button>
              </li>
            ))}
          </ul>
        </Banner>
      )}

      {items.filter((item) => item.status !== "done").length > 0 && (
        <ul className="document-list" data-testid="upload-queue" aria-live="polite">
          {items
            .filter((item) => item.status !== "done")
            .map((item) => (
              <UploadQueueRow key={item.localId} item={item} onCancel={cancelUpload} onRetry={retryFailedItem} onRemove={removeItem} />
            ))}
        </ul>
      )}

      {duplicatePrompt && (
        <DuplicateFileDialog
          fileName={duplicatePrompt.fileName}
          onReplace={() => resolveDuplicate("replace")}
          onKeepBoth={() => resolveDuplicate("keep_both")}
          onCancel={() => resolveDuplicate("cancel")}
        />
      )}

      {loading ? (
        <div data-testid="documents-skeleton">
          <Skeleton height={48} style={{ marginBottom: 8 }} />
          <Skeleton height={48} style={{ marginBottom: 8 }} />
          <Skeleton height={48} />
        </div>
      ) : variant === "ES-01" || variant === "ES-05" ? (
        <EmptyState
          data-testid="empty-state"
          title={variant === "ES-01" ? uiText.es01Title : uiText.es05Title}
          description={variant === "ES-01" ? uiText.es01Description : uiText.es05Description}
        />
      ) : variant === "ES-02" ? (
        <EmptyState data-testid="empty-state" title={uiText.es02Title} description={uiText.es02Description} />
      ) : variant === "ES-03" ? (
        <Banner tone="danger" data-testid="empty-state">
          <strong>{uiText.es03Title}</strong> — {uiText.es03Description}
        </Banner>
      ) : (
        <ul className="document-list" data-testid="doc-list">
          {documents.map((doc) => (
            <li key={doc.id} className="document-row" data-testid="doc-item">
              <div className="document-row__main">
                <span className="document-row__name" title={doc.name}>
                  <strong>{doc.name}</strong>
                </span>
                <small>
                  <StatusBadge status={doc.status} errorCode={doc.errorCode} expiresAt={doc.expiresAt} />
                  {doc.status === "ready" && doc.pageCount ? ` · ${formatNumber(doc.pageCount)} trang` : ""}
                </small>
              </div>
              <div className="document-row__actions">
                {doc.status === "failed" && doc.errorCode && RETRYABLE_ERRORS.has(doc.errorCode) && (
                  <Button
                    type="button"
                    variant="secondary"
                    data-testid="doc-retry"
                    disabled={retrying.has(doc.id)}
                    onClick={() => void retry(doc)}
                  >
                    {uiText.retry}
                  </Button>
                )}
                <Button type="button" variant="ghost" data-testid="doc-delete" onClick={() => setPendingDelete(doc)}>
                  Xóa
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <DeleteConfirmDialog
        open={pendingDelete !== null}
        fileName={pendingDelete?.name ?? ""}
        pending={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </section>
  );
}

function UploadQueueRow({
  item,
  onCancel,
  onRetry,
  onRemove,
}: {
  item: UploadItem;
  onCancel: (localId: string) => void;
  onRetry: (localId: string) => void;
  onRemove: (localId: string) => void;
}) {
  return (
    <li className="upload-queue-row" data-testid="upload-queue-item" aria-live="polite">
      <div className="upload-queue-row__top">
        <span className="upload-queue-row__name" title={item.file.name}>
          {item.file.name}
        </span>
        {item.status === "uploading" && (
          <Button type="button" variant="ghost" onClick={() => onCancel(item.localId)}>
            {uiText.cancelUpload}
          </Button>
        )}
        {item.status === "failed" && (
          <>
            <Button type="button" variant="secondary" onClick={() => onRetry(item.localId)}>
              {uiText.retry}
            </Button>
            <Button type="button" variant="ghost" onClick={() => onRemove(item.localId)}>
              Xóa
            </Button>
          </>
        )}
      </div>
      {item.status === "uploading" || item.status === "queued" ? (
        <div className="upload-progress" role="progressbar" aria-valuenow={item.progress} aria-valuemin={0} aria-valuemax={100}>
          <div className="upload-progress__bar" style={{ width: `${item.status === "queued" ? 0 : item.progress}%` }} />
        </div>
      ) : (
        <StatusBadge status="failed" errorCode={item.errorCode} />
      )}
    </li>
  );
}
