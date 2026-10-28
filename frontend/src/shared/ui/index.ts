// Barrel export cho shared/ui (SDD §3.2.3). Mọi component ở đây thuần
// hiển thị — không import shared/api, shared/analytics hay features/*.
export { Button, type ButtonProps, type ButtonVariant } from "./Button";
export { IconButton, type IconButtonProps } from "./IconButton";
export { Badge, type BadgeProps, type BadgeTone } from "./Badge";
export { Dialog, DialogClose, type DialogProps } from "./Dialog";
export {
  ToastProvider,
  ToastRegion,
  useToast,
  type ToastInput,
  type ToastTone,
  type ToastRegionProps,
} from "./Toast";
export { Tooltip, type TooltipProps } from "./Tooltip";
export { Skeleton, type SkeletonProps } from "./Skeleton";
export { Banner, type BannerProps, type BannerTone } from "./Banner";
export { EmptyState, type EmptyStateProps } from "./EmptyState";
export { OfflineBanner, type OfflineBannerProps } from "./OfflineBanner";
export { Drawer, type DrawerProps } from "./Drawer";
