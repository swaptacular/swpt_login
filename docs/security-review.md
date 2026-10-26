# Security and bug review: swpt_login

| | |
|---|---|
| Reviewed commit | `208d7c8` (2026-07-18) |
| Review date | 2026-10-26 |
| Scope | `swpt_login/` (routes, Redis records, emails, CAPTCHA/ALTCHA, Hydra client, templates) |
| Method | Manual code review; findings reproduced with PostgreSQL 16, Redis 7 and a local SMTP sink, using the project's test configuration |

This document covers the issues **fixed in this pull request**, plus
review notes. Additional findings that are not fixed here have been
reported to the maintainers privately.

## Summary

| ID | Severity | Finding | Status |
|---|---|---|---|
| SEC-1 | High | Reflected XSS on four report pages | Fixed |
| SEC-2 | Medium | Open redirect in `/language/<lang>?to=` | Fixed |
| SEC-3 | Low | HTML injection into outgoing emails | Fixed |

## SEC-1: Reflected XSS on report pages (High, fixed)

**Where:** `report_sent_email.html`, `report_email_change_failure.html`,
`report_email_change_success.html`,
`report_account_deletion_success.html` (and `report_signup_success.html`).

**Problem.** These templates build an HTML snippet with
`'<em class="email">{}</em>'.format(email)|safe`. `str.format` inserts
the value without escaping, and `|safe` then switches off Jinja's
autoescaping. Four of the routes take the email address straight from
the query string:

| Route | Parameter |
|---|---|
| `/login/email` | `email` |
| `/login/change-email-failure` | `new_email` |
| `/login/change-email-success` | `old_email`, `new_email` |
| `/login/account-deletion-success` | `email` |

A link such as
`/login/email?email=<script>alert(document.domain)</script>` runs the
script on the login origin. There is no Content-Security-Policy. A
script on the login origin can, for example, replace the page with a
fake login form, and it runs same-origin with the consent pages.

**Reproduction.** All four routes returned 200 with the raw
`<script>` element in the body.

**Fix.** The value is escaped before formatting:
`'<em class="email">{}</em>'.format(email|e)|safe`.

**Test:** `test_reported_email_is_escaped` (5 cases).

## SEC-2: Open redirect in language selection (Medium, fixed)

**Where:** `swpt_login/routes.py`, `set_language`.

**Problem.** `/login/language/<lang>?to=<url>` redirected to any URL.
On the login domain this makes a convincing phishing redirector.

```
?to=https://evil.example/phish   → 302 Location: https://evil.example/phish
?to=//evil.example               → 302 Location: //evil.example
?to=javascript:alert(1)          → 302 Location: javascript:alert(1)
```

**Fix.** `is_safe_redirect_url()` allows only relative paths (`/…`, but
not `//…`) and absolute `http`/`https` URLs on the current host. It
rejects backslashes, whitespace and control characters, which browsers
may normalize into a different host. Anything else redirects to `/`.
The language links in `layout.html` (`to=request.url`) keep working.

**Test:** `test_set_language_redirect_target` (10 cases).

## SEC-3: HTML injection into outgoing emails (Low, fixed)

**Where:** `swpt_login/emails.py`, `text_to_html`.

**Problem.** The plain-text email body is converted to HTML by wrapping
paragraphs in `<p>`, without escaping. The text includes values such as
the email address and the parsed `User-Agent` of the login attempt, so
markup in those values ended up as live HTML in the email.

**Fix.** Paragraphs, link lines and signature lines are now escaped
with `html.escape`. None of the `.txt` email templates contain
intentional HTML.

**Test:** three new assertions in `test_text_to_html`.

## Review notes

- **Brute-force protection.** Login and the other password forms
  require a single-use ALTCHA proof-of-work solution (on by default).
  Login verification codes, recovery codes and secret links have
  per-user or per-request failure limits (`SECRET_CODE_MAX_ATTEMPTS`).
  Email-sending endpoints are limited per IP address.
- **Two-factor login.** A new device needs both the verification cookie
  (proving knowledge of the password) and the emailed code. Known
  devices are remembered by hashed "computer codes".
- **Account deletion** requires the password again on the confirmation
  page, so access to the user's email alone is not enough.
- **Framing.** `X-Frame-Options: DENY` is set on all responses, which
  prevents clickjacking of the consent page.
- **Consent CSRF.** The consent `POST` has no CSRF token, but it needs
  the unguessable `consent_challenge`, which a cross-site attacker
  cannot read.
- **Other `|safe` uses** (`redirect_url`, `recovery_code`, `title`,
  CAPTCHA HTML) use server-generated values only.

## Tests

- `test_reported_email_is_escaped` (5 cases)
- `test_set_language_redirect_target` (10 cases)
- new assertions in `test_text_to_html`

Each fails without its fix. Full suite: 63 passed; `flake8` clean. The
tests need PostgreSQL, Redis and an SMTP server.
