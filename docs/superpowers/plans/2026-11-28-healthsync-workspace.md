# HealthSync sign-in and workspace refresh

User-authorized scope: match the sign-in and signed-in experience to the landing page; remove Ask from the profile-section tabs and make it a dedicated action. Work in the existing checkout and preserve all earlier uncommitted landing/rename work, data and credentials. No commits or pushes. Leave the running app available for the user.

Design: reuse Manrope, forest green, muted mint, original illustration and the shared wordmark. Authentication has an illustrative left panel and a clear form with labelled fields, password visibility and correct password-manager autocomplete. Preserve sign-in, account creation and password recovery request behaviour. The private workspace uses a restrained sidebar and top bar, responsive mobile navigation, clearer family/profile headers and common form/card treatment. Profile header contains an actual Ask HealthSync button navigating to the existing profile-scoped ask route; all other tab routes, permissions and source links remain unchanged. No new clinical features or medical claims.

Alternatives considered: changing only colors (does not address navigation hierarchy); rebuilding the entire app (unnecessary risk); selected shell/form/header updates plus scoped shared styles (chosen).

Tasks:
1. Test the dedicated Ask action and password visibility/autocomplete before implementation. Preserve existing profile routing and authentication checks.
2. Add shared theme and icon primitives, restyle authentication while retaining submit logic.
3. Restyle workspace shell, family/profile navigation and chat presentation. Preserve data queries and access rules.
4. Run full frontend tests with the already-established UTC test environment, production build, desktop/mobile browser checks, no-overflow and keyboard checks. Review code, address findings, and keep the live development services running.

## Verification completed

- Dedicated profile Ask button replaces the Ask tab and navigates to the same profile-scoped route. Existing reports, clinical fields and permissions unchanged.
- Correct current-password/new-password autocomplete and show/hide controls tested; changing authentication mode hides and clears the password.
- Landing section navigation and skip controls now use focus/scroll actions without fragments. Source-report URLs no longer use PDF page fragments. BrowserRouter remains in place.
- All 107 frontend tests pass in the established TZ=UTC test environment (21 files); production build passes. Existing local/UTC doctor-sheet date-boundary issue is outside this change.
- Browser flow checks passed at 1440×1000, 375×812, 812×375 and 320×740: no horizontal overflow or uncaught errors, sign-in, account layout, family/profile navigation, dedicated Ask, sourced example answer, normal URL paths and keyboard menu focus. Screenshots use synthetic fixtures only.
- Password recovery, reset, registration, and normal-motion auth art were checked independently in the browser.
- Review findings fixed: all auth illustration animations disabled, and mobile workspace nav moves focus to main after a destination is selected. Reviewer confirmed both resolutions.
- Current frontend/backend/worker/infrastructure services remain running for user testing. No data/credential changes, staging, commit or push.

## User revision: simplify and revert workspace visuals

The user requested sign-in without the body diagram or marketing panel, and the original signed-in UI with the separate Ask button retained. Removed the entire illustrative auth aside and extra marketing elements; centred the account form. Restored the original Layout, FamilyPage, ChatPanel and profile tab styling while preserving HealthSync branding, password usability improvements, the dedicated profile-scoped Ask button and hash-free navigation. Replaced workspace-wide styling with auth-only CSS, leaving the private app's original Tailwind design intact.

Verification: 107 frontend tests passed; production build passed. Desktop 1440px and mobile 375px browser checks confirmed no sign-in illustration/marketing panel, no sidebar, original profile UI and functioning separate Ask action with no Ask tab. Services remain running. No commits or pushes.
