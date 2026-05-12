"use client";

import * as React from "react";
import Collapse from "@mui/material/Collapse";

interface CollapsibleContextValue {
  open: boolean;
  disabled?: boolean;
  setOpen: (next: boolean) => void;
}

const CollapsibleContext = React.createContext<CollapsibleContextValue | null>(
  null,
);

function useCollapsibleContext() {
  const context = React.useContext(CollapsibleContext);
  if (!context) {
    throw new Error("CollapsibleTrigger/Content must be used within Collapsible");
  }
  return context;
}

interface CollapsibleProps extends React.ComponentProps<"div"> {
  open?: boolean;
  defaultOpen?: boolean;
  disabled?: boolean;
  onOpenChange?: (open: boolean) => void;
}

function Collapsible({
  open: controlledOpen,
  defaultOpen = false,
  disabled,
  onOpenChange,
  children,
  ...props
}: CollapsibleProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(defaultOpen);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : uncontrolledOpen;

  const setOpen = React.useCallback(
    (next: boolean) => {
      if (disabled) return;
      if (!isControlled) {
        setUncontrolledOpen(next);
      }
      onOpenChange?.(next);
    },
    [disabled, isControlled, onOpenChange],
  );

  return (
    <CollapsibleContext.Provider value={{ open, setOpen, disabled }}>
      <div data-slot="collapsible" {...props}>
        {children}
      </div>
    </CollapsibleContext.Provider>
  );
}

interface CollapsibleTriggerProps
  extends Omit<React.ComponentProps<"button">, "onClick"> {
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
}

function CollapsibleTrigger({
  onClick,
  disabled,
  children,
  type,
  ...props
}: CollapsibleTriggerProps) {
  const { open, setOpen, disabled: rootDisabled } = useCollapsibleContext();
  const isDisabled = disabled ?? rootDisabled ?? false;

  const handleClick: React.MouseEventHandler<HTMLButtonElement> = (event) => {
    onClick?.(event);
    if (!event.defaultPrevented) {
      setOpen(!open);
    }
  };

  return (
    <button
      data-slot="collapsible-trigger"
      type={type ?? "button"}
      disabled={isDisabled}
      {...props}
      onClick={handleClick}
    >
      {children}
    </button>
  );
}

function CollapsibleContent({
  children,
  forceMount,
  ...props
}: React.ComponentProps<"div"> & { forceMount?: boolean }) {
  const { open } = useCollapsibleContext();
  return (
    <Collapse
      in={open}
      timeout="auto"
      unmountOnExit={!forceMount}
      collapsedSize={0}
    >
      <div data-slot="collapsible-content" {...props}>
        {children}
      </div>
    </Collapse>
  );
}

export { Collapsible, CollapsibleTrigger, CollapsibleContent };
