import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useSearchParams } from "react-router-dom";
import Brand from "../components/Brand";
import HealthIcon from "../components/HealthIcon";
import { accountHome, useAuth } from "../auth";
import { auth } from "../api/endpoints";
import { Button, ErrorAlert, TextField, errorMessage } from "../components/ui";

export default function LoginPage() {
  const { user, login, register } = useAuth();
  const location = useLocation();
  const [params] = useSearchParams();
  const [mode, setMode] = useState<"signin" | "register" | "forgot" | "reset">(params.get("mode") === "register" ? "register" : "signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [token, setToken] = useState("");
  const [notice, setNotice] = useState("");
  const [showPassword, setShowPassword] = useState(false);

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
        setShowPassword(false);
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
    setShowPassword(false);
  }

  return (
    <div className="hs-auth">
      <header className="hs-auth-header">
        <Link to="/about" aria-label="About HealthSync"><Brand /></Link>
        <Link to="/about" className="hs-auth-back"><HealthIcon name="back" />Back to home</Link>
      </header>
      <main className="hs-auth-layout">
        <section className="hs-auth-form-area" aria-labelledby="auth-title">
          <div className="hs-auth-form-content">
            <h1 id="auth-title">{title}</h1>
            <p className="hs-auth-intro">{isRegister ? "Create your HealthSync account." : isForgot ? "Enter your email to request a password reset." : isReset ? "Choose a new password for your health space." : "Enter your email and password to continue."}</p>
            <form onSubmit={submit} className="hs-auth-form">
              <TextField label="Email" type="email" autoComplete="email" required value={email} placeholder="you@example.com" onChange={(e) => setEmail(e.target.value)} />
              {isReset && <TextField label="Reset token" required value={token} onChange={(e) => setToken(e.target.value)} hint="Paste the token from the local backend log." />}
              {!isForgot && <div className="hs-password-field">
                <TextField label="Password" type={showPassword ? "text" : "password"} required
                  autoComplete={isRegister || isReset ? "new-password" : "current-password"}
                  minLength={isRegister || isReset ? 10 : undefined}
                  hint={isRegister || isReset ? "At least 10 characters. A short sentence is easy to remember." : undefined}
                  value={password} onChange={(e) => setPassword(e.target.value)} />
                <button className="hs-password-toggle" type="button" aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} onClick={() => setShowPassword(v => !v)}><HealthIcon name={showPassword ? "eyeOff" : "eye"} /></button>
              </div>}
              {!isRegister && !isForgot && !isReset && <div className="hs-auth-forgot"><Button variant="link" type="button" onClick={() => switchMode("forgot")}>Forgot password?</Button></div>}
              <ErrorAlert>{error}</ErrorAlert>
              {notice && <p role="status" className="hs-auth-notice">{notice}</p>}
              <Button type="submit" disabled={busy} className="hs-auth-submit">{busy ? "Please wait…" : title}{!busy && <HealthIcon name="arrow" />}</Button>
            </form>
            {isForgot && <p className="hs-auth-switch"><Button variant="link" type="button" onClick={() => switchMode("reset")}>I have a reset token</Button></p>}
            {(isForgot || isReset) && <p className="hs-auth-switch"><Button variant="link" type="button" onClick={() => switchMode("signin")}>Back to sign in</Button></p>}
            {!isReset && <p className="hs-auth-switch">{isRegister ? "Already have an account? " : "New to HealthSync? "}<Button variant="link" type="button" onClick={() => switchMode(isRegister ? "signin" : "register")}>{isRegister ? "Sign in" : "Create an account"}</Button></p>}
            <p className="hs-auth-clinician">For clinicians: <Link to="/doctor/register">Register as a doctor</Link></p>
          </div>
        </section>
      </main>
    </div>
  );
}
