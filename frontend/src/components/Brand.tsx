/** A single wordmark for public pages and the signed-in application. */
export default function Brand({ className = "" }: { className?: string }) {
  return <span className={`healthsync-brand ${className}`}>
    <svg viewBox="0 0 36 36" width="34" height="34" fill="none" aria-hidden="true">
      <rect x="1" y="1" width="34" height="34" rx="11" fill="currentColor" />
      <path d="M9 18h5l3-7 4 14 3-7h3" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
    <span>HealthSync<span className="healthsync-brand-dot">.</span></span>
  </span>;
}
