import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./Button.css";

const VARIANTS = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  ghost: "btn-ghost",
  danger: "btn-danger",
} as const;

const SIZES = {
  sm: "btn-sm",
  md: "btn-md",
  lg: "btn-lg",
} as const;

type ButtonVariant = keyof typeof VARIANTS;
type ButtonSize = keyof typeof SIZES;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
}

export default function Button({
  children,
  variant = "primary",
  size = "md",
  type = "button",
  disabled = false,
  loading = false,
  fullWidth = false,
  className = "",
  ...props
}: ButtonProps) {
  const classes = [
    "btn",
    VARIANTS[variant],
    SIZES[size],
    fullWidth ? "btn-full" : "",
    loading ? "btn-loading" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="btn-spinner" aria-hidden="true" />}
      <span className={loading ? "btn-label-loading" : ""}>{children}</span>
    </button>
  );
}
