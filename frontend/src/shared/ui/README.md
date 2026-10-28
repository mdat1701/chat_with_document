# shared/ui

Design system thuần hiển thị (SDD §3.2.3): `Button`, `IconButton`, `Badge`,
`Dialog`, `Toast` + `ToastRegion`, `Tooltip`, `Skeleton`, `Banner`,
`EmptyState` — `Dialog`/`Tooltip` bọc Radix UI. Import duy nhất từ
`@shared/ui` (xem `index.ts`). Không component nào gọi API hay import
`shared/api`/`shared/analytics`/`features/*`. Mọi phần tử tương tác nhận
`data-testid`. Mỗi component có smoke test axe-core đi kèm (`*.test.tsx`).
