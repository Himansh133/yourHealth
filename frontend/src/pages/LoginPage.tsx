import { useState, type FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth";
import { Button, ErrorAlert, TextField, errorMessage } from "../components/ui";

export default function LoginPage() {
  const { user, login, register } = useAuth();
  const location = useLocation();
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={(location.state as { from?: string } | null)?.from ?? "/"} replace />;

  const isRegister = mode === "register";
  const title = isRegister ? "Create account" : "Sign in";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await (isRegister ? register : login)(email, password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto mt-16 max-w-sm px-4">
      <p className="mb-6 text-2xl font-semibold text-teal-800">YourHealth</p>
      <h1 className="mb-4 text-xl font-semibold">{title}</h1>
      <form onSubmit={submit} className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <TextField label="Email" type="email" autoComplete="email" required value={email}
          onChange={(e) => setEmail(e.target.value)} />
        <TextField label="Password" type="password" required
          autoComplete={isRegister ? "new-password" : "current-password"}
          minLength={isRegister ? 10 : undefined}
          hint={isRegister ? "At least 10 characters. A short sentence is easy to remember." : undefined}
          value={password} onChange={(e) => setPassword(e.target.value)} />
        <ErrorAlert>{error}</ErrorAlert>
        <Button type="submit" disabled={busy}>
          {busy ? "Please wait…" : title}
        </Button>
      </form>
      <p className="mt-4 text-sm text-slate-600">
        {isRegister ? "Already have an account? " : "New here? "}
        <Button variant="link" type="button" onClick={() => { setMode(isRegister ? "signin" : "register"); setError(""); }}>
          {isRegister ? "Sign in" : "Create an account"}
        </Button>
      </p>
    </main>
  );
}
