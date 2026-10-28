import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { logout } from "@shared/api/client";
import { useAuth, type CurrentUser } from "@features/auth/auth";
import { clearDraft } from "@features/auth/draft";
import { uiText } from "@shared/i18n/messages.vi";

/**
 * Menu người dùng ở `AppHeader` (T-405 §5.5) — chỉ 3 mục theo SDD v0.3:
 * thông tin tài khoản (nhãn, không bấm được), "Trợ giúp", "Đăng xuất".
 * Không còn Báo cáo tuần/Chấm điểm/Quản lý quyền (post-MVP, đã loại bỏ).
 * Dùng Radix UI Dropdown Menu để có sẵn điều hướng bằng mũi tên và `Esc`.
 */
export function UserMenu() {
  const user = useAuth((state) => state.user);
  if (!user) return null;
  return <UserMenuContent user={user} />;
}

function UserMenuContent({ user }: { user: CurrentUser }) {
  const label = user.display_name ?? user.email;

  const handleLogout = () => {
    clearDraft();
    void logout().finally(() => {
      window.location.href = "/login";
    });
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          className="ui-button ui-button--ghost"
          data-testid="user-menu-trigger"
        >
          {label}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="app-user-menu__content"
          align="end"
          sideOffset={6}
          data-testid="user-menu"
        >
          <DropdownMenu.Label
            className="app-user-menu__label"
            data-testid="user-menu-account"
          >
            {user.email}
          </DropdownMenu.Label>
          <DropdownMenu.Separator className="app-user-menu__separator" />
          <DropdownMenu.Item
            className="app-user-menu__item"
            data-testid="user-menu-help"
            onSelect={() => {
              window.open(
                "mailto:support@example.com",
                "_blank",
                "noopener,noreferrer",
              );
            }}
          >
            {uiText.userMenuHelp}
          </DropdownMenu.Item>
          <DropdownMenu.Item
            className="app-user-menu__item"
            data-testid="user-menu-logout"
            onSelect={handleLogout}
          >
            {uiText.userMenuLogout}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
