import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { accountHome, useAuth } from "../auth";
import { auth } from "../api/endpoints";
import { Button, ErrorAlert, TextField, errorMessage } from "../components/ui";

export default function LoginPage() {
  const { user, login, register } = useAuth();
  const location = useLocation();
  const [mode, setMode] = useState<"signin" | "register" | "forgot" | "reset">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [token, setToken] = useState("");
  const [notice, setNotice] = useState("");

  if (user) return <Navigate to={user.account_type === "patient"
    ? (location.state as { from?: string } | null)?.from ?? "/" : accountHome(user.account_type)} replace />;

  const isRegister = mode === "register";
  const isForgot = mode === "forgot";
  const isReset = mode === "reset";
  const title = isRegister ? "Create account" : isForgot ? "Forgot password" : isReset ? "Reset password" : "Sign in";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNotice("");
    setBusy(true);
    try {
      if (isForgot) {
        const result = await auth.requestPasswordReset(email);
        setNotice(result.message);
      } else if (isReset) {
        await auth.confirmPasswordReset(token, password);
        setNotice("Password reset. You can now sign in.");
        setMode("signin");
        setPassword("");
        setToken("");
      } else {
        await (isRegister ? register : login)(email, password);
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function switchMode(next: typeof mode) {
    setMode(next);
    setError("");
    setNotice("");
    setPassword("");
  }

  return (
    <main className="mx-auto mt-16 max-w-sm px-4">
      <p className="mb-6 text-2xl font-semibold text-teal-800">YourHealth</p>
      <h1 className="mb-4 text-xl font-semibold">{title}</h1>
      <form onSubmit={submit} className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <TextField label="Email" type="email" autoComplete="email" required value={email}
          onChange={(e) => setEmail(e.target.value)} />
        {isReset && <TextField label="Reset token" required value={token} onChange={(e) => setToken(e.target.value)} hint="Paste the token from the local backend log." />}
        {!isForgot && <TextField label="Password" type="password" required
          autoComplete={isRegister ? "new-password" : "new-password"}
          minLength={isRegister || isReset ? 10 : undefined}
          hint={isRegister || isReset ? "At least 10 characters. A short sentence is easy to remember." : undefined}
          value={password} onChange={(e) => setPassword(e.target.value)} />}
        <ErrorAlert>{error}</ErrorAlert>
        {notice && <p role="status" className="rounded-md bg-teal-50 px-3 py-2 text-sm text-teal-900">{notice}</p>}
        <Button type="submit" disabled={busy}>
          {busy ? "Please wait…" : title}
        </Button>
      </form>
      {!isRegister && !isForgot && !isReset && <p className="mt-3 text-sm"><Button variant="link" type="button" onClick={() => switchMode("forgot")}>Forgot password?</Button></p>}
      {isForgot && <p className="mt-3 text-sm"><Button variant="link" type="button" onClick={() => switchMode("reset")}>I have a reset token</Button></p>}
      {(isForgot || isReset) && <p className="mt-3 text-sm"><Button variant="link" type="button" onClick={() => switchMode("signin")}>Back to sign in</Button></p>}
      {!isReset && <p className="mt-4 text-sm text-slate-600">
        {isRegister ? "Already have an account? " : "New here? "}
        <Button variant="link" type="button" onClick={() => switchMode(isRegister ? "signin" : "register")}>
          {isRegister ? "Sign in" : "Create an account"}
        </Button>
      </p>}
      <p className="mt-3 text-sm text-slate-600">
        For clinicians: <Link to="/doctor/register" className="inline-flex min-h-11 items-center text-teal-700 underline">Register as a doctor</Link>.
        {" "}Existing doctors and admins use the sign-in form above.
      </p>
    </main>
  );
}
