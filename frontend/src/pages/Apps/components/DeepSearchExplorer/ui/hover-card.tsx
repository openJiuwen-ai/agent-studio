"use client";

import * as React from "react";
import Paper from "@mui/material/Paper";
import Popper, { type PopperProps } from "@mui/material/Popper";

import { cn } from "./utils";

type Side = "top" | "right" | "bottom" | "left";
type Align = "start" | "center" | "end";

function resolvePlacement(side: Side, align: Align): PopperProps["placement"] {
  if (align === "center") return side;
  return `${side}-${align}` as PopperProps["placement"];
}

function isElementOfType<P>(
  child: React.ReactNode,
  component: React.ComponentType<P>,
): child is React.ReactElement<P> {
  return React.isValidElement(child) && child.type === component;
}

function composeEventHandler<E extends React.SyntheticEvent>(
  original?: (event: E) => void,
  injected?: (event: E) => void,
) {
  return (event: E) => {
    original?.(event);
    if (!event.defaultPrevented) {
      injected?.(event);
    }
  };
}

interface HoverCardRootProps {
  openDelay?: number;
  closeDelay?: number;
  children: React.ReactNode;
}

function HoverCard({
  openDelay = 700,
  closeDelay = 300,
  children,
}: HoverCardRootProps) {
  const childArray = React.Children.toArray(children);
  const triggerElement = childArray.find((child) =>
    isElementOfType(child, HoverCardTrigger),
  );
  const contentElement = childArray.find((child) =>
    isElementOfType(child, HoverCardContent),
  );

  const [open, setOpen] = React.useState(false);
  const [anchorEl, setAnchorEl] = React.useState<HTMLElement | null>(null);
  const openTimerRef = React.useRef<number | null>(null);
  const closeTimerRef = React.useRef<number | null>(null);

  const clearOpenTimer = React.useCallback(() => {
    if (openTimerRef.current !== null) {
      window.clearTimeout(openTimerRef.current);
      openTimerRef.current = null;
    }
  }, []);

  const clearCloseTimer = React.useCallback(() => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }, []);

  const scheduleOpen = React.useCallback(
    (anchor: HTMLElement) => {
      clearCloseTimer();
      clearOpenTimer();
      openTimerRef.current = window.setTimeout(() => {
        setAnchorEl(anchor);
        setOpen(true);
      }, openDelay);
    },
    [clearCloseTimer, clearOpenTimer, openDelay],
  );

  const scheduleClose = React.useCallback(() => {
    clearOpenTimer();
    clearCloseTimer();
    closeTimerRef.current = window.setTimeout(() => {
      setOpen(false);
    }, closeDelay);
  }, [clearCloseTimer, clearOpenTimer, closeDelay]);

  React.useEffect(() => {
    return () => {
      clearOpenTimer();
      clearCloseTimer();
    };
  }, [clearCloseTimer, clearOpenTimer]);

  if (!triggerElement || !contentElement) {
    return <>{children}</>;
  }

  const {
    children: triggerChildren,
    asChild = false,
  } = triggerElement.props;

  const {
    className,
    align = "center",
    side = "bottom",
    sideOffset = 4,
    children: contentChildren,
    ...contentProps
  } = contentElement.props;

  const triggerNode = asChild
    ? (React.Children.only(triggerChildren) as React.ReactElement)
    : <span>{triggerChildren}</span>;

  const triggerElementNode = React.isValidElement(triggerNode)
    ? (triggerNode as React.ReactElement<Record<string, unknown>>)
    : null;

  const enhancedTrigger = React.isValidElement(triggerNode)
    ? React.cloneElement(triggerElementNode!, {
        onMouseEnter: composeEventHandler(
          triggerElementNode?.props.onMouseEnter as
            | ((event: React.MouseEvent<HTMLElement>) => void)
            | undefined,
          (event: React.MouseEvent<HTMLElement>) => {
            scheduleOpen(event.currentTarget);
          },
        ),
        onMouseLeave: composeEventHandler(
          triggerElementNode?.props.onMouseLeave as
            | ((event: React.MouseEvent<HTMLElement>) => void)
            | undefined,
          () => scheduleClose(),
        ),
        onFocus: composeEventHandler(
          triggerElementNode?.props.onFocus as
            | ((event: React.FocusEvent<HTMLElement>) => void)
            | undefined,
          (event: React.FocusEvent<HTMLElement>) => {
            scheduleOpen(event.currentTarget);
          },
        ),
        onBlur: composeEventHandler(
          triggerElementNode?.props.onBlur as
            | ((event: React.FocusEvent<HTMLElement>) => void)
            | undefined,
          () => scheduleClose(),
        ),
      })
    : null;

  return (
    <>
      {enhancedTrigger}
      <Popper
        open={open}
        anchorEl={anchorEl}
        placement={resolvePlacement(side, align)}
        modifiers={[
          {
            name: "offset",
            options: { offset: [0, sideOffset] },
          },
        ]}
        sx={{ zIndex: 1500 }}
      >
        <Paper
          data-slot="hover-card-content"
          className={cn(
            "bg-popover text-popover-foreground rounded-md border p-4 shadow-md outline-hidden",
            className,
          )}
          onMouseEnter={clearCloseTimer}
          onMouseLeave={scheduleClose}
          {...contentProps}
        >
          {contentChildren}
        </Paper>
      </Popper>
    </>
  );
}

interface HoverCardTriggerProps {
  asChild?: boolean;
  children: React.ReactNode;
}

function HoverCardTrigger({
  children,
}: HoverCardTriggerProps) {
  return <>{children}</>;
}

interface HoverCardContentProps extends React.ComponentProps<"div"> {
  align?: Align;
  side?: Side;
  sideOffset?: number;
}

function HoverCardContent({
  ...props
}: HoverCardContentProps) {
  return <>{props.children}</>;
}

HoverCardTrigger.displayName = "HoverCardTrigger";
HoverCardContent.displayName = "HoverCardContent";

export { HoverCard, HoverCardTrigger, HoverCardContent };
