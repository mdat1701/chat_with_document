import type { ReactNode } from "react";
import * as RadixTooltip from "@radix-ui/react-tooltip";
import "./ui.css";

export type TooltipProps = {
  content: string;
  children: ReactNode;
  "data-testid"?: string;
};

/** Gợi ý ngắn khi di/focus vào phần tử, bọc Radix UI. Thuần hiển thị. */
export function Tooltip({
  content,
  children,
  "data-testid": testId,
}: TooltipProps) {
  return (
    <RadixTooltip.Provider delayDuration={200}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            className="ui-tooltip-content"
            sideOffset={6}
            data-testid={testId}
          >
            {content}
            <RadixTooltip.Arrow className="ui-tooltip-arrow" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}
