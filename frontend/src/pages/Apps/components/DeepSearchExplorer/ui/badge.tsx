import * as React from "react";

import { cn } from "./utils";

type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

const BADGE_FRAME_TOKENS = [
  "inline-flex",
  "items-center",
  "justify-center",
  "rounded-md",
  "border",
  "px-2",
  "py-0.5",
  "text-xs",
  "font-medium",
  "w-fit",
  "whitespace-nowrap",
  "shrink-0",
  "overflow-hidden",
] as const;

const BADGE_FRAME = BADGE_FRAME_TOKENS.join(" ");

const resolveVariantClasses = (variant: BadgeVariant): string => {
  switch (variant) {
    case "secondary":
      return "border-transparent bg-secondary text-secondary-foreground";
    case "destructive":
      return "border-transparent bg-destructive text-white";
    case "outline":
      return "text-foreground";
    case "default":
    default:
      return "border-transparent bg-primary text-primary-foreground";
  }
};

const badgeVariants = ({
  variant = "default",
  className,
}: {
  variant?: BadgeVariant;
  className?: string;
} = {}) =>
  cn(
    BADGE_FRAME,
    resolveVariantClasses(variant),
    className,
  );

interface BadgeProps
  extends Omit<React.ComponentProps<"span">, "color"> {
  variant?: BadgeVariant;
  asChild?: boolean;
}

function Badge({
  className,
  variant = "default",
  asChild = false,
  children,
  ...props
}: BadgeProps) {
  const mergedClassName = badgeVariants({ variant, className });

  if (asChild && React.isValidElement(children)) {
    const child = children as React.ReactElement<{ className?: string }>;
    return React.cloneElement(child, {
      ...props,
      className: cn(mergedClassName, child.props.className),
    });
  }

  return (
    <span
      data-slot="badge"
      className={mergedClassName}
      {...props}
    >
      {children}
    </span>
  );
}

export { Badge, badgeVariants };
