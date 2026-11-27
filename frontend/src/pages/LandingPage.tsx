import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { accountHome, useAuth } from "../auth";
import Brand from "../components/Brand";
import HealthIllustration, { type HealthArea } from "../components/HealthIllustration";
import "./landing.css";

function Icon({ name, className = "" }: { name: "arrow" | "report" | "shield" | "spark" | "heart" | "trend" | "people" | "check"; className?: string }) {
  const paths = {
    arrow: "M5 12h14m-6-6 6 6-6 6",
    report: "M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9m-6-6v6h6M8 13h8M8 17h5M14 3l6 6",
    shield: "M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3Zm-4 9 3 3 5-6",
    spark: "m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z",
    heart: "M20.5 5.5a5 5 0 0 0-7 0L12 7l-1.5-1.5a5 5 0 0 0-7 7L12 21l8.5-8.5a5 5 0 0 0 0-7ZM3 12h5l2-3 3 6 2-3h6",
    trend: "M4 5v14h16M7 14l4-4 4 3 5-7",
    people: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M15 3.13a4 4 0 0 1 0 7.75M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
    check: "m5 12 4 4L19 6",
  };
  return <svg className={className} width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}

const AREAS = {
  heart: { label: "Heart & circulation", test: "LDL cholesterol", value: "96", unit: "mg/dL", panel: "Lipid panel", hint: "A little more context for every number." },
  metabolic: { label: "Metabolic health", test: "HbA1c", value: "7.2", unit: "%", panel: "Glucose profile", hint: "Follow the same test across your reports." },
  kidney: { label: "Kidney health", test: "Creatinine", value: "0.9", unit: "mg/dL", panel: "Kidney function", hint: "Keep the value connected to its source." },
} satisfies Record<HealthArea, { label: string; test: string; value: string; unit: string; panel: string; hint: string }>;

const QUESTIONS = [
  { question: "What changed in my reports?", summary: "Your example HbA1c reading fell by 0.4 percentage points.", detail: "7.6% on 12 Mar → 7.2% on 14 Jun 2026. A change in a number alone does not establish an improvement in health." },
  { question: "Where did this answer come from?", summary: "This comparison comes from two example reports.", detail: "The earlier reading is 7.6% on 12 Mar 2026. The later reading is 7.2% on 14 Jun 2026. The source links below let you check both." },
  { question: "Can I keep my family’s reports here?", summary: "Yes. Each family member has a separate profile.", detail: "Upload records to the person they belong to. Questions and comparisons use the selected profile, so family histories stay separate." },
];

export default function LandingPage() {
  const { user } = useAuth();
  const [area, setArea] = useState<HealthArea>("heart");
  const [question, setQuestion] = useState(0);
  const [paused, setPaused] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const record = AREAS[area];
  const destination = user ? accountHome(user.account_type) : "/login?mode=register";

  function scrollToSection(id: string) {
    setMenuOpen(false);
    const target = document.getElementById(id);
    target?.focus({ preventScroll: true });
    target?.scrollIntoView({ block: "start", behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ? "instant" : "smooth" });
  }

  return <div className="healthsync-landing" data-paused={paused}>
    <button className="hs-skip" onClick={() => scrollToSection("main-content")}>Skip to content</button>
    <header className="hs-header" onKeyDown={e => { if (e.key === "Escape" && menuOpen) { setMenuOpen(false); menuButton.current?.focus(); } }}>
      <div className="hs-nav-wrap">
        <Link to="/" aria-label="HealthSync home"><Brand /></Link>
        <nav id="healthsync-navigation" aria-label="Main navigation" className={`hs-navigation ${menuOpen ? "is-open" : ""}`}>
          <button type="button" onClick={() => scrollToSection("how-it-works")}>How it works</button>
          <button type="button" onClick={() => scrollToSection("connected-care")}>The bigger picture</button>
          <button type="button" onClick={() => scrollToSection("your-control")}>Your privacy</button>
        </nav>
        <div className="hs-nav-actions">
          <Link className="hs-signin" to={user ? accountHome(user.account_type) : "/login"}>{user ? "Open your space" : "Sign in"}</Link>
          <Link className="hs-button hs-button-small" to={destination}>{user ? "Dashboard" : "Get started"}<Icon name="arrow" /></Link>
          <button ref={menuButton} className="hs-menu-toggle" aria-label={menuOpen ? "Close navigation" : "Open navigation"} aria-expanded={menuOpen} aria-controls="healthsync-navigation" onClick={() => setMenuOpen(v => !v)}>
            <svg width="22" height="22" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d={menuOpen ? "m6 6 12 12M6 18 18 6" : "M4 8h16M4 16h16"} /></svg>
          </button>
        </div>
      </div>
    </header>

    <main id="main-content" tabIndex={-1}>
      <section className="hs-hero hs-container" aria-labelledby="hero-title">
        <div className="hs-hero-copy">
          <p className="hs-eyebrow"><span className="hs-status-dot" /> A little clarity. A healthier connection.</p>
          <h1 id="hero-title">Every report.<br />One connected<br /><span>health story.</span></h1>
          <p className="hs-hero-description">Your reports hold a bigger picture. Bring them together, understand what changed, and find answers you can trace back to the source.</p>
          <div className="hs-hero-actions">
            <Link className="hs-button" to={destination}>{user ? "Go to your health space" : "Create your HealthSync account"}<Icon name="arrow" /></Link>
            <button type="button" className="hs-text-link" onClick={() => scrollToSection("see-it-in-action")}><span className="hs-play-icon">▷</span> Take a closer look</button>
          </div>
          <div className="hs-hero-reassurance"><Icon name="shield" /><span>For you and the people you care for.</span></div>
        </div>

        <div className="hs-health-scene">
          <div className="hs-scene-topline"><span className="hs-small-label">THE BIGGER PICTURE</span><span className="hs-scene-coordinate">Connected, by you.</span></div>
          <HealthIllustration active={area} />
          <div className="hs-area-controls" aria-label="Explore example health records">
            {(Object.keys(AREAS) as HealthArea[]).map(key => <button key={key} className={`hs-area-control hs-area-${key}`} aria-pressed={area === key} onClick={() => setArea(key)}>
              <span className="hs-area-dot" /><span>{AREAS[key].label}</span><span className="hs-area-plus" aria-hidden="true">+</span>
            </button>)}
          </div>
          <div className="hs-sample-record" aria-label="Example record" aria-live="polite" aria-atomic="true">
            <div className="hs-record-top"><span><Icon name="report" />{record.panel}</span><span className="hs-record-source"><span /> SOURCE LINKED</span></div>
            <div className="hs-record-main" key={area}>
              <div><p>{record.test}</p><strong>{record.value}<span>{record.unit}</span></strong></div>
              <svg viewBox="0 0 125 45" width="125" height="45" className="hs-record-line" aria-hidden="true"><path d="M2 29 17 25 31 30 46 18 61 23 76 11 91 16 105 8 122 12" fill="none" stroke="currentColor" strokeWidth="2" /><circle cx="122" cy="12" r="3" fill="currentColor" /></svg>
            </div>
            <div className="hs-record-bottom"><span>Sample lab · 14 Jun 2026</span><span>{record.hint}</span></div>
          </div>
          <div className="hs-scene-caption"><span>Illustrative data · Not a real patient</span><button onClick={() => setPaused(v => !v)} aria-label={paused ? "Play illustration" : "Pause illustration"} aria-pressed={paused}><svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true">{paused ? <path d="m4 2 8 5-8 5Z" /> : <path d="M3 2h3v10H3zm5 0h3v10H8z" />}</svg></button></div>
        </div>
      </section>

      <div className="hs-principles hs-container" aria-label="What HealthSync brings together">
        <p>A more connected way<br /><strong>to understand your health.</strong></p>
        <span><Icon name="report" /> Your records, together</span><span><Icon name="trend" /> Changes, made clearer</span><span><Icon name="spark" /> Answers, with evidence</span>
      </div>

      <section id="connected-care" tabIndex={-1} className="hs-connected hs-container">
        <div className="hs-section-heading"><p className="hs-eyebrow">LOOK BEYOND A SINGLE REPORT</p><h2>Small details.<br /><span>A fuller picture.</span></h2><p>A result makes more sense with its history. HealthSync helps you follow that thread, from the original report to the next conversation with your doctor.</p></div>
        <div className="hs-feature-grid">
          <article className="hs-feature hs-feature-records"><div className="hs-feature-icon"><Icon name="report" /></div><h3>A home for your health records.</h3><p>Lab reports, prescriptions and extracted readings, organised around the person they belong to.</p><div className="hs-file-stack" aria-hidden="true"><div><span className="hs-file-mini"><Icon name="report" /></span><span>Blood test report<small>14 June 2026</small></span><span className="hs-file-check"><Icon name="check" /></span></div><div><span className="hs-file-mini"><Icon name="report" /></span><span>Prescription<small>12 March 2026</small></span><span className="hs-file-check"><Icon name="check" /></span></div></div><span className="hs-feature-footnote">Illustrative records</span></article>
          <article className="hs-feature hs-feature-trends"><div className="hs-feature-icon"><Icon name="trend" /></div><h3>See the change over time.</h3><p>Compare dated, compatible readings. Keep the original values and units close at hand.</p><div className="hs-trend-preview" aria-label="Illustrative HbA1c readings: 7.6 percent in March and 7.2 percent in June"><div><span>HbA1c</span><span>Two reports, one view</span></div><svg viewBox="0 0 300 95" fill="none" aria-hidden="true"><path d="M0 20H300M0 55H300M0 90H300" stroke="#d4e1d9" strokeDasharray="3 4" /><path d="M25 20C100 20 140 76 275 76" stroke="#497664" strokeWidth="2.5" /><circle cx="25" cy="20" r="4" fill="#497664" /><circle cx="275" cy="76" r="4" fill="#497664" /></svg><div><span>Mar · 7.6%</span><span>Jun · 7.2%</span></div></div><span className="hs-feature-footnote">Example values, not a clinical assessment</span></article>
          <article className="hs-feature hs-feature-family"><div className="hs-feature-icon"><Icon name="people" /></div><h3>Care has a wider circle.</h3><p>Give each family member their own space. Prepare a doctor sheet when it’s time for an appointment.</p><div className="hs-family-preview" aria-hidden="true"><span className="hs-family-person"><span>A</span>You<small>Your profile</small></span><span className="hs-family-person"><span>M</span>Mum<small>Separate records</small></span><span className="hs-family-person"><span>D</span>Dad<small>Separate records</small></span></div><span className="hs-feature-footnote">Different people. Their own histories.</span></article>
        </div>
      </section>

      <section id="see-it-in-action" tabIndex={-1} className="hs-evidence-section">
        <div className="hs-container hs-evidence-grid">
          <div className="hs-evidence-copy"><p className="hs-eyebrow">A QUESTION. A CLEARER NEXT STEP.</p><h2>More understanding.<br /><span>Less searching.</span></h2><p>Ask in everyday language, in English or Hindi. Read a concise answer and follow its sources back to the records.</p><div className="hs-question-list" aria-label="Try an example question">{QUESTIONS.map((q,i)=><button key={q.question} onClick={()=>setQuestion(i)} aria-pressed={question===i}>{q.question}<Icon name="arrow" /></button>)}</div><p className="hs-example-note">An interactive example. Your personal answers use your selected profile’s records.</p></div>
          <div className="hs-answer-card" aria-label="Example answer" aria-live="polite" aria-atomic="true">
            <div className="hs-answer-header"><Brand /><span>AN EXAMPLE CONVERSATION</span></div>
            <div className="hs-question-bubble">{QUESTIONS[question].question}</div>
            <div className="hs-answer-body" key={question}><span className="hs-answer-spark"><Icon name="spark" /></span><h3>{QUESTIONS[question].summary}</h3><p>{QUESTIONS[question].detail}</p><span className="hs-evidence-label">CHECK THE EXAMPLE SOURCES</span><div className="hs-source-links"><a href="/demo/sample-2026-03-12.pdf" target="_blank" rel="noreferrer"><Icon name="report" /><span>12 Mar 2026<small>Example lab report · opens PDF</small></span><span>↗</span></a><a href="/demo/sample-2026-06-14.pdf" target="_blank" rel="noreferrer"><Icon name="report" /><span>14 Jun 2026<small>Example lab report · opens PDF</small></span><span>↗</span></a></div></div>
            <div className="hs-answer-note"><Icon name="shield" /> A source to check. A conversation to have.</div>
          </div>
        </div>
      </section>

      <section id="how-it-works" tabIndex={-1} className="hs-how hs-container">
        <div className="hs-section-heading hs-heading-wide"><p className="hs-eyebrow">SIMPLE TO BEGIN. EASY TO COME BACK TO.</p><h2>A little organisation.<br /><span>A lot more context.</span></h2></div>
        <div className="hs-steps">{[
          ["01", "Bring your records.", "Create a profile and upload a supported PDF or photo of a report."],
          ["02", "Check the details.", "Review extracted readings against the original. Handwriting may need correction."],
          ["03", "Connect the dots.", "Explore comparisons, ask questions and prepare your next doctor visit."],
        ].map(([n,title,detail])=><article key={n}><span className="hs-step-number">{n}</span><h3>{title}</h3><p>{detail}</p></article>)}</div>
      </section>

      <section id="your-control" tabIndex={-1} className="hs-privacy hs-container">
        <div className="hs-privacy-art" aria-hidden="true"><div className="hs-shield-orbit" /><div className="hs-shield-orbit hs-shield-orbit-two" /><div className="hs-shield-center"><Icon name="shield" /></div><span className="hs-privacy-label">PERSONAL, BY DESIGN</span></div>
        <div><p className="hs-eyebrow">YOUR HEALTH IS PERSONAL</p><h2>Keep the context.<br /><span>Keep the control.</span></h2><p>Your records belong in the right profile. Original documents stay available, and you choose the scope when creating a shared doctor sheet.</p><ul><li><Icon name="check" /> Separate records for each family member</li><li><Icon name="check" /> Source documents beside extracted readings</li><li><Icon name="check" /> Scoped, time-limited summary sharing</li></ul><p className="hs-clinical-note">HealthSync helps you organise and understand records. It does not diagnose conditions or replace advice from a qualified clinician.</p></div>
      </section>

      <section className="hs-final-cta hs-container"><span className="hs-small-label">A CLEARER PICTURE STARTS HERE</span><h2>Your health story,<br /><span>all coming together.</span></h2><p>Make a little space for the bigger picture.</p><Link className="hs-button" to={destination}>{user ? "Open your health space" : "Create your account"}<Icon name="arrow" /></Link><div className="hs-cta-rings" aria-hidden="true" /></section>
    </main>
    <footer className="hs-footer hs-container"><div><Link to="/" aria-label="HealthSync home"><Brand /></Link><p>A little clarity, for a little more peace of mind.</p></div><div className="hs-footer-links"><button type="button" onClick={() => scrollToSection("how-it-works")}>How it works</button><button type="button" onClick={() => scrollToSection("your-control")}>Privacy &amp; control</button><Link to="/doctor/register">Register as a doctor</Link></div><div className="hs-footer-bottom"><span>© {new Date().getFullYear()} HealthSync</span><span>Built around your records. Designed around you.</span></div></footer>
  </div>;
}
