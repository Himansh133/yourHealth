import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { Button } from "./ui";

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white print:hidden">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-semibold text-teal-800">
            YourHealth
          </Link>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <Link to="/settings/whatsapp" className="text-teal-700 hover:underline">WhatsApp</Link>
            <span className="hidden sm:inline">{user?.email}</span>
            <Button variant="secondary" className="!px-3 !py-1 text-sm" onClick={() => void logout()}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
    </div>
  );
}
