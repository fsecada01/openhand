# Security Policy

OpenHand serves people experiencing financial hardship — a
population heavily targeted by scams. Security and privacy issues
here can cause real-world harm, so reports are taken seriously and
handled quickly.

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

- Preferred: [GitHub private vulnerability reporting](https://github.com/fsecada01/openhand/security/advisories/new)
- Or email: **francis.secada@gmail.com** (subject: `[openhand security]`)

You can expect an acknowledgment within 72 hours. Please include
reproduction steps and impact; coordinated disclosure is
appreciated and you'll be credited unless you prefer otherwise.

## In scope

Beyond classic web vulnerabilities, we treat these as security
issues:

- Any path that stores or leaks narratives, PII, or API keys
  (including via logs or error messages)
- Prompt-injection that makes the intake/explanation passes emit
  personal data or alter presented determinations
- Rate-limit bypasses that enable abuse of the LLM endpoints

## Supported versions

Pre-1.0: only the latest `main` receives fixes.
