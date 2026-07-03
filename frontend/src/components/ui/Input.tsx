import type { InputHTMLAttributes } from "react";
import "./Input.css";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export default function Input({
  id,
  label,
  error,
  hint,
  className = "",
  ...props
}: InputProps) {
  const inputId = id ?? props.name;

  return (
    <div className={`input-field ${className}`.trim()}>
      {label && (
        <label htmlFor={inputId} className="input-label">
          {label}
        </label>
      )}
      <input id={inputId} className={`input ${error ? "input-error" : ""}`} {...props} />
      {error && (
        <p className="input-error-text" role="alert">
          {error}
        </p>
      )}
      {!error && hint && <p className="input-hint">{hint}</p>}
    </div>
  );
}
