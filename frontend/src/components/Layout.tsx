import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { accountHome, useAuth } from "../auth";
import { Button } from "./ui";
import Brand from "./Brand";

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white print:hidden">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to={user ? accountHome(user.account_type) : "/"} className="text-lg font-semibold text-teal-800">
            <Brand className="!text-lg" />
          </Link>
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
            {user?.account_type === "patient" && <Link to="/demo" className="text-teal-700 hover:underline">Demo</Link>}
            {user?.account_type === "patient" && <Link to="/evaluation" className="text-teal-700 hover:underline">Evaluation</Link>}
            {user?.account_type === "patient" && <Link to="/settings/whatsapp" className="text-teal-700 hover:underline">WhatsApp</Link>}
            {user?.account_type === "doctor" && <span>Doctor portal</span>}
            {user?.account_type === "admin" && <span>Administration</span>}
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
