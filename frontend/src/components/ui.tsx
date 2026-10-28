import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { useId } from "react";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "link" }) {
  const styles = {
    primary: "bg-teal-700 text-white hover:bg-teal-800 disabled:bg-slate-400 px-4 py-2 rounded-md font-medium",
    secondary: "border border-slate-300 bg-white hover:bg-slate-50 px-4 py-2 rounded-md font-medium",
    link: "text-teal-700 underline-offset-2 hover:underline",
  }[variant];
  return (
    <button
      className={`${styles} focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 ${className}`}
      {...props}
    />
  );
}

export function TextField({
  label,
  hint,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={id}
        aria-describedby={hint ? `${id}-hint` : undefined}
        className="rounded-md border border-slate-300 px-3 py-2 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
        {...props}
      />
      {hint && (
        <p id={`${id}-hint`} className="text-xs text-slate-500">
          {hint}
        </p>
      )}
    </div>
  );
}

export function ErrorAlert({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
      {children}
    </p>
  );
}

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong. Please try again.";
}
