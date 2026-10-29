import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { whatsapp } from "../api/endpoints";
import type { WhatsAppLinkCode, WhatsAppStatus } from "../api/types";
import { Button, ErrorAlert, errorMessage } from "../components/ui";
import { formatDate } from "../format";

/** Settings → Connect WhatsApp (plan 3.3): the user sends "LINK <code>" to the bot from their phone. */
export default function WhatsAppPage({ pollMs = 3000 }: { pollMs?: number }) {
  const [status, setStatus] = useState<WhatsAppStatus | null>(null);
  const [code, setCode] = useState<WhatsAppLinkCode | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    whatsapp.status().then(setStatus).catch((e) => setError(errorMessage(e)));
  }, []);

  // While a code is showing, check every few seconds whether the phone has linked.
  useEffect(() => {
    if (!code || status?.linked) return;
    const timer = setInterval(() => {
      whatsapp.status().then((s) => {
        setStatus(s);
        if (s.linked) setCode(null);
      }).catch(() => undefined);
    }, pollMs);
    return () => clearInterval(timer);
  }, [code, status?.linked, pollMs]);

  async function getCode() {
    setError("");
    try {
      setCode(await whatsapp.linkCode());
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function disconnect() {
    setError("");
    try {
      await whatsapp.unlink();
      setStatus(await whatsapp.status());
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  const message = code ? `LINK ${code.code}` : "";
  const botDigits = code?.bot_number.replace(/\D/g, "") ?? "";

  return (
    <section className="flex max-w-xl flex-col gap-4">
      <div>
        <Link to="/" className="text-sm text-teal-700 hover:underline">← Family</Link>
        <h1 className="mt-1 text-2xl font-semibold">Connect WhatsApp</h1>
        <p className="mt-1 text-slate-600">
          Forward lab reports and prescriptions to the YourHealth bot, and ask questions like "papa ka sugar kaisa hai?".
          Replies are short and link back here; full reports never go into the chat.
        </p>
      </div>
      <ErrorAlert>{error}</ErrorAlert>
      {status === null && !error && <p className="text-slate-500">Loading…</p>}

      {status?.linked && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4">
          <p>
            Connected: <span className="font-medium">{status.phone}</span>
            {status.linked_at && <span className="text-slate-500"> since {formatDate(status.linked_at.slice(0, 10))}</span>}
          </p>
          <Button variant="secondary" onClick={disconnect}>Disconnect</Button>
        </div>
      )}

      {status && !status.linked && !code && <div><Button onClick={getCode}>Get a code</Button></div>}

      {code && (
        <div className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-4">
          <p>From your phone, send this message on WhatsApp:</p>
          <p className="text-2xl font-semibold tracking-wider">{message}</p>
          {code.bot_number ? (
            <>
              <p>to <span className="font-medium">{code.bot_number}</span></p>
              <a href={`https://wa.me/${botDigits}?text=${encodeURIComponent(message)}`} target="_blank" rel="noreferrer"
                className="self-start rounded-md bg-teal-700 px-4 py-2 font-medium text-white hover:bg-teal-800">
                Open WhatsApp with this message
              </a>
            </>
          ) : (
            <p className="text-amber-800">The WhatsApp bot isn't set up on this server yet (no bot number configured).</p>
          )}
          <p className="text-sm text-slate-500">The code works for 10 minutes. This page updates once you're connected.</p>
        </div>
      )}
    </section>
  );
}
