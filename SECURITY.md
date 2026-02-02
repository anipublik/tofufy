# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | Yes       |

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for security vulnerabilities.

Instead, use GitHub's private vulnerability reporting:  
**Security → Report a vulnerability** on the repository page.

We aim to acknowledge reports within 48 hours and publish a fix within 14 days for critical issues.

## Design notes

- tofufy never stores or logs API keys, tokens, or state files beyond what you explicitly write to disk.
- No telemetry, no analytics, no network calls except to TFE/GitHub/GitLab/Bitbucket APIs you configure.
- LLM API keys are passed through `litellm` directly to the provider; tofufy never sees or stores the response beyond the current process.
