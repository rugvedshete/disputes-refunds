import { useState, type FormEvent } from "react";
import { useAuth } from "../auth";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("agent@example.com");
  const [password, setPassword] = useState("agent1234");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try { await login(email, password); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <div className="login">
      <form onSubmit={submit} className="panel">
        <h1>Sign in</h1>
        <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        {error && <p className="inline-error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <p className="hint">Demo accounts: agent@example.com / agent1234, customer@example.com / customer1234</p>
      </form>
    </div>
  );
}
