# 7. Doctor sheet, sharing and privacy

## 7.1 The doctor visit sheet

One page per family member, built entirely from SQL, with no language model involved:

- name, age and sex (nothing else that identifies the person);
- **values outside the report's range** in the chosen period (3, 6 or 12 months), each with the value before it;
- **worth discussing about medicines:** the flagged insights from Section 5.3, with label links;
- **trends:** small charts for tests with at least two values in the period;
- **current medicines** with ingredients and start dates;
- **reports included**, with links;
- a footer: "Values are copied from the reports by YourHealth. Check them against the original reports listed above."

It prints cleanly from the browser (the app's header and tabs are hidden when printing), which also gives a PDF.

## 7.2 Sharing by QR code and PIN

A family member picks how long the link should work (1 hour, 24 hours or 7 days) and gets a QR code and a 4-digit
PIN, shown once. The doctor scans the QR code, types the PIN the family tells them, and sees the sheet on their
phone. No account is needed.

| Risk | Control |
|---|---|
| A forwarded QR photo gives anyone the sheet | The link alone is not enough: the PIN is told separately |
| The database leaks | Only a SHA-256 hash of the 32-byte random token and an Argon2 hash of the PIN are stored |
| Someone guesses the PIN | Five wrong PINs lock the link |
| The link lives forever | It expires (1 h / 24 h / 7 d), and the family can turn it off at any time |
| The sheet changes after sharing, or shows more than intended | The doctor sees a frozen snapshot made when the link was created, and can open only the reports listed on it |
| A doctor's session for one link opens another | The session cookie is scoped to that link's path and names the link it unlocked |
| Nobody knows who looked | Every open is logged; the family sees "opened 3 times, last 30 Oct 19:28" |

## 7.3 Privacy and security measures

- **Authentication:** passwords hashed with Argon2; a signed session token in an httpOnly cookie (Secure in
  deployment); the signing secret must be at least 32 bytes.
- **Authorisation:** one permission check on every profile-scoped route (Section 3.5); non-members get 404 so the API
  doesn't reveal that a profile exists.
- **Files:** a private bucket; files are served only through the API after the permission check; the upload type is
  checked from the file's bytes.
- **Untrusted documents:** document text reaches the language model only inside an evidence block marked as data;
  the validator blocks medicine advice whatever the model writes; treatment questions never reach the model's
  answer-writing step. In the evaluation no planted instruction was followed (0 of 5, every system).
- **WhatsApp:** every webhook is checked against Meta's signature; phones are linked only with a one-time code that
  expires in 10 minutes; five wrong codes lock that phone for an hour; failed attempts are logged by a hash of the
  phone number, not the number.
- **Third parties:** no patient data goes to the drug-data APIs (they were called once, offline, with generic drug
  names). Questions and the person's evidence *are* sent to the LLM provider; a deployment would need a provider
  agreement, or a local model behind the same interface.
- **Logs** record IDs and error types, never document text.
- **Development data** is synthetic: no real patient's report was used.

**Not done (future work):** a review against India's Digital Personal Data Protection Act 2023, consent records,
data export and deletion on request, and encryption at rest beyond what the storage provides.

## 7.4 Checked in a real browser

Every screen was driven in Chrome (Playwright) at 1280, 390 and 360 px wide: the reports, trends, medicines and ask
tabs, the doctor sheet, creating a share link, and the doctor's PIN page on a phone. This found six problems that unit
tests and the evaluation had missed:

- Hindi answers about HbA1c always came back in English.
- Medicine-name answers fell back to the facts table.
- Converted values were shown unrounded ("118.9056 mg/dL").
- The sheet's medicine card contradicted its own table.
- Report links on loaded data returned a server error.
- The profile tabs ran off a phone screen.

All six were fixed (problems 5.4, 7.7, 8.17, 8.18).
