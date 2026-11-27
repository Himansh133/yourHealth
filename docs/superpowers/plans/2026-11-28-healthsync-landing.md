# HealthSync rename and public landing page

User-authorized scope: rename the application to HealthSync and build an interactive healthcare landing page inspired by the supplied Dribbble reference and screenshot. Implement in the existing checkout; preserve unrelated untracked work and existing accounts/data. No commits, pushes or publication.

## Design

Use the existing React/Vite/router stack. Public `/` displays an editorial healthcare introduction: ivory/mint surfaces, navy typography, original anatomical SVG illustration, interactive record examples, concise feature/workflow sections, evidence explanation and an account CTA. Existing authenticated patients retain their family home at `/`; doctor/admin routing remains intact. `/about` lets signed-in visitors see the public introduction. All main CTAs use the existing login/registration flow. Decorative animation respects reduced-motion and is pausable. All example values are clearly labelled synthetic. Do not advertise clinical validation, complete doctor access or handwriting accuracy.

Approaches considered: an embedded reference video (poor accessibility and dependency on third-party media); a WebGL scene (unnecessary weight); native SVG/CSS interaction (selected for original artwork, responsiveness, keyboard access and small runtime cost). The supplied reference guides the aesthetic; the browser screenshot is not a landing asset.

## Tasks

1. Add meaningful route/interaction checks: visitors see landing, authenticated patients retain family home, clicking a body-system control changes the example and source, question selection updates sample evidence, registration CTA opens registration.
2. Rename visible branding across frontend, document footer, shared summaries, API title, WhatsApp messages, app metadata and README. Retain DB/user/bucket identifiers and historical evaluation/report artifacts to preserve compatibility and provenance.
3. Add scoped landing styles, a shared brand component, native anatomical illustration, accessible interactions and responsive navigation. Keep patient data out of the public page.
4. Wire public routes and account CTAs; keep existing private-route protections and doctor/admin routing.
5. Run frontend suite and production build, targeted backend branding/import checks, desktop/mobile browser checks and reduced-motion/keyboard checks. Review diff and keep services stopped after temporary UI verification.

## Verification

Check no stale visible name remains in application files; template-derived demos should use the new name without rewriting medical values. Confirm no credential/data files are staged, changed or published. Existing report DOCX files in Downloads are outside this request.

## Completed verification

- Renamed visible branding and metadata, including dashboard export generation. Original evaluation outputs, database identities, private credentials and existing clinical records were preserved.
- Existing baseline: 98 frontend tests passed; one pre-existing doctor-sheet assertion fails near local/UTC day boundaries under Asia/Kolkata. No doctor-sheet logic changed.
- Final frontend suite: 105 passed with TZ=UTC, 21 files. Known jsdom/Recharts zero-width warnings remain in existing chart tests.
- Backend: 29 targeted health/WhatsApp checks passed; the evaluation-dashboard export check also passed. No live WhatsApp or provider requests made.
- Production build passed without bundle-size warnings after lazy-loading the profile screen: initial JS 246.58 kB, profile JS 443.14 kB before gzip.
- Browser checks passed at 1440×1000, 375×812, 812×375 and 320×740: no horizontal overflow or uncaught errors, working anatomy controls, question/evidence switching, downloadable example PDFs, registration navigation, mobile menu Escape/focus and reduced motion.
- Independent review caught an auth-loading flash; fixed and covered with a deferred-session regression. Reviewer confirmed resolution.
- Screenshot: /home/himansh/Downloads/HealthSync-preview.png. Temporary frontend and database stopped after verification. No commit or push.
