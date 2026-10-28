import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import "./ui.css";

export type ToastTone = "neutral" | "success" | "warning" | "danger";

export type ToastInput = {
  title: string;
  description?: string;
  tone?: ToastTone;
  /** ms trước khi tự ẩn; mặc định 5000. Truyền 0 để giữ cho tới khi đóng tay. */
  duration?: number;
};

type ToastRecord = ToastInput & { id: string };

type ToastContextValue = {
  toasts: ToastRecord[];
  showToast: (toast: ToastInput) => string;
  dismissToast: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

/**
 * Nguồn trạng thái cho hệ thống Toast dùng chung. Thuần hiển thị — chỉ giữ
 * danh sách thông báo trong state React, không gọi API hay phân tích.
 * Bọc `<ToastProvider>` quanh ứng dụng và đặt `<ToastRegion>` bên trong.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const counter = useRef(0);

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback((toast: ToastInput) => {
    counter.current += 1;
    const id = `toast-${counter.current}`;
    setToasts((current) => [
      ...current,
      { id, duration: 5000, tone: "neutral", ...toast },
    ]);
    return id;
  }, []);

  const value = useMemo(
    () => ({ toasts, showToast, dismissToast }),
    [toasts, showToast, dismissToast],
  );

  return (
    <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
  );
}

/** Hook phát thông báo toast từ bất kỳ đâu trong cây component. */
export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast phải dùng bên trong <ToastProvider>");
  return { showToast: ctx.showToast, dismissToast: ctx.dismissToast };
}

export type ToastRegionProps = { "data-testid"?: string };

/** Vùng hiển thị toast, đặt một lần ở gốc ứng dụng. */
export function ToastRegion({ "data-testid": testId }: ToastRegionProps = {}) {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("ToastRegion phải dùng bên trong <ToastProvider>");
  const { toasts, dismissToast } = ctx;

  return (
    <div className="ui-toast-region" aria-live="polite" data-testid={testId}>
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          onDismiss={() => dismissToast(toast.id)}
        />
      ))}
    </div>
  );
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: ToastRecord;
  onDismiss: () => void;
}) {
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  if (!timerRef.current && toast.duration !== 0) {
    timerRef.current = setTimeout(onDismiss, toast.duration ?? 5000);
  }
  const isAlert = toast.tone === "danger" || toast.tone === "warning";
  return (
    <div
      role={isAlert ? "alert" : "status"}
      className={["ui-toast", `ui-toast--${toast.tone ?? "neutral"}`].join(" ")}
      data-testid="toast-item"
    >
      <div className="ui-toast__body">
        <p className="ui-toast__title">{toast.title}</p>
        {toast.description ? (
          <p className="ui-toast__description">{toast.description}</p>
        ) : null}
      </div>
      <button
        type="button"
        className="ui-icon-button"
        aria-label="Đóng thông báo"
        data-testid="toast-dismiss"
        onClick={onDismiss}
      >
        ×
      </button>
    </div>
  );
}
