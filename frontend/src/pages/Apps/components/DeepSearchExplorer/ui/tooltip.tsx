"use client";

import * as React from "react";
import MuiTooltip, { type TooltipProps as MuiTooltipProps } from "@mui/material/Tooltip";

import { cn } from "./utils";

type Side = "top" | "right" | "bottom" | "left";
type Align = "start" | "center" | "end";

function resolvePlacement(side: Side, align: Align): MuiTooltipProps["placement"] {
  if (align === "center") return side;
  return `${side}-${align}` as MuiTooltipProps["placement"];
}

function isElementOfType<P>(
  child: React.ReactNode,
  component: React.ComponentType<P>,
): child is React.ReactElement<P> {
  return React.isValidElement(child) && child.type === component;
}

interface TooltipProviderProps {
  delayDuration?: number;
  children: React.ReactNode;
}

function TooltipProvider({
  delayDuration = 0,
  ...props
}: TooltipProviderProps) {
  void delayDuration;
  return <>{props.children}</>;
}

interface TooltipRootProps {
  delayDuration?: number;
  children: React.ReactNode;
}

function Tooltip({
  delayDuration = 0,
  children,
}: TooltipRootProps) {
  const childArray = React.Children.toArray(children);
  const triggerElement = childArray.find((child) =>
    isElementOfType(child, TooltipTrigger),
  );
  const contentElement = childArray.find((child) =>
    isElementOfType(child, TooltipContent),
  );

  if (!triggerElement || !contentElement) {
    return <>{children}</>;
  }

  const {
    children: triggerChildren,
    asChild = false,
  } = triggerElement.props;

  const {
    className,
    side = "top",
    align = "center",
    sideOffset = 0,
    children: contentChildren,
    ...contentProps
  } = contentElement.props;

  const triggerNode = asChild
    ? (React.Children.only(triggerChildren) as React.ReactElement)
    : <span>{triggerChildren}</span>;

  return (
    <TooltipProvider delayDuration={delayDuration}>
      <MuiTooltip
        title={<div {...contentProps}>{contentChildren}</div>}
        enterDelay={delayDuration}
        placement={resolvePlacement(side, align)}
        arrow
        slotProps={{
          tooltip: {
            className: cn(
              "bg-primary text-primary-foreground rounded-md px-3 py-1.5 text-xs",
              className,
            ),
          },
          popper: {
            modifiers: [
              {
                name: "offset",
                options: { offset: [0, sideOffset] },
              },
            ],
          },
        }}
      >
        {triggerNode}
      </MuiTooltip>
    </TooltipProvider>
  );
}

interface TooltipTriggerProps {
  asChild?: boolean;
  children: React.ReactNode;
}

function TooltipTrigger({
  children,
}: TooltipTriggerProps) {
  return <>{children}</>;
}

interface TooltipContentProps extends React.ComponentProps<"div"> {
  side?: Side;
  align?: Align;
  sideOffset?: number;
}

function TooltipContent({
  children,
}: TooltipContentProps) {
  return <>{children}</>;
}

TooltipTrigger.displayName = "TooltipTrigger";
TooltipContent.displayName = "TooltipContent";

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider };
