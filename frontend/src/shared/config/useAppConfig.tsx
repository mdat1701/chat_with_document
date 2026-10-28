import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiFetch } from "@shared/api/client";
import { DEFAULT_APP_CONFIG, type AppConfig } from "./appConfig";

type AppConfigContextValue = {
  config: AppConfig;
  loading: boolean;
  /** true nếu GET /config lỗi và UI đang dùng giá trị mặc định an toàn. */
  usedFallback: boolean;
};

const AppConfigContext = createContext<AppConfigContextValue | null>(null);

/**
 * Nạp `GET /config` một lần khi khởi động (T-106 §5.7, P-06: không hard-code
 * giới hạn trong UI). Nếu lỗi, dùng DEFAULT_APP_CONFIG và không chặn đăng
 * nhập — đúng mục "Trường hợp biên" trong tài liệu task.
 */
export function AppConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AppConfig>(DEFAULT_APP_CONFIG);
  const [loading, setLoading] = useState(true);
  const [usedFallback, setUsedFallback] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiFetch<AppConfig>("/config")
      .then((value) => {
        if (!cancelled) setConfig(value);
      })
      .catch(() => {
        if (!cancelled) {
          setConfig(DEFAULT_APP_CONFIG);
          setUsedFallback(true);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({ config, loading, usedFallback }),
    [config, loading, usedFallback],
  );

  return (
    <AppConfigContext.Provider value={value}>
      {children}
    </AppConfigContext.Provider>
  );
}

/** Đọc cấu hình hệ thống (giới hạn tệp, số câu hỏi, …) — không hard-code. */
export function useAppConfig() {
  const ctx = useContext(AppConfigContext);
  if (!ctx)
    throw new Error("useAppConfig phải dùng bên trong <AppConfigProvider>");
  return ctx;
}
