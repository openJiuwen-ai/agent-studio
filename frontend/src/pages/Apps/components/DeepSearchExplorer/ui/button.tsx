import * as React from "react";
import ButtonMui from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";

import { cn } from "./utils";

type ButtonVariant =
  | "default"
  | "destructive"
  | "outline"
  | "secondary"
  | "ghost"
  | "link";

type ButtonSize = "default" | "sm" | "lg" | "icon";

const buttonBaseClassName =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 shrink-0";

const buttonVariantClassNames: Record<ButtonVariant, string> = {
  default: "bg-primary text-primary-foreground hover:bg-primary/90",
  destructive: "bg-destructive text-white hover:bg-destructive/90",
  outline:
    "border bg-background text-foreground hover:bg-accent hover:text-accent-foreground",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  ghost: "hover:bg-accent hover:text-accent-foreground",
  link: "text-primary underline-offset-4 hover:underline",
};

const buttonSizeClassNames: Record<ButtonSize, string> = {
  default: "h-9 px-4 py-2",
  sm: "h-8 px-3",
  lg: "h-10 px-6",
  icon: "size-9",
};

const buttonVariants = ({
  variant = "default",
  size = "default",
  className,
}: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
} = {}) =>
  cn(
    buttonBaseClassName,
    buttonVariantClassNames[variant],
    buttonSizeClassNames[size],
    className,
  );

interface ButtonProps
  extends Omit<React.ComponentProps<"button">, "color"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  asChild?: boolean;
}

function resolveMuiVariant(variant: ButtonVariant) {
  switch (variant) {
    case "outline":
      return "outlined" as const;
    case "ghost":
    case "link":
      return "text" as const;
    default:
      return "contained" as const;
  }
}

function resolveMuiColor(variant: ButtonVariant) {
  switch (variant) {
    case "destructive":
      return "error" as const;
    case "secondary":
      return "secondary" as const;
    case "outline":
    case "ghost":
    case "link":
      return "inherit" as const;
    default:
      return "primary" as const;
  }
}

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  children,
  ...props
}: ButtonProps) {
  const sharedClassName = buttonVariants({ variant, size, className });

  if (asChild) {
    if (React.isValidElement(children)) {
      const child = children as React.ReactElement<{ className?: string }>;
      return React.cloneElement(child, {
        ...props,
        className: cn(sharedClassName, child.props.className),
      });
    }
    return (
      <button data-slot="button" className={sharedClassName} {...props}>
        {children}
      </button>
    );
  }

  if (size === "icon") {
    return (
      <IconButton
        data-slot="button"
        color={resolveMuiColor(variant)}
        size="small"
        className={sharedClassName}
        {...props}
      >
        {children}
      </IconButton>
    );
  }

  return (
    <ButtonMui
      data-slot="button"
      variant={resolveMuiVariant(variant)}
      color={resolveMuiColor(variant)}
      size={size === "lg" ? "large" : size === "sm" ? "small" : "medium"}
      className={sharedClassName}
      {...props}
    >
      {children}
    </ButtonMui>
  );
}

export { Button, buttonVariants };
