import { create } from "zustand";
import { apiFetch, setCsrfToken } from "@shared/api/client";

export type CurrentUser = {
  id: string;
  email: string;
  display_name: string | null;
  roles: string[];
  csrf_token: string;
};

type AuthState = {
  user: CurrentUser | null;
  loading: boolean;
  load: () => Promise<void>;
};

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  load: async () => {
    try {
      const user = await apiFetch<CurrentUser>("/me");
      setCsrfToken(user.csrf_token);
      set({ user, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },
}));
