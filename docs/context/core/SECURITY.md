# Security Development Rules

## Scope

These rules apply to local development, Claude-assisted coding,
Git commits, tests, API integration, and future deployment.


## Secrets

Never commit:

- .env
- API keys
- access tokens
- passwords
- private keys
- cloud credentials
- OAuth secrets
- service-account credentials

Real secrets belong only in ignored local environment files or an
approved secret-management system.

.env.example may contain variable names and safe placeholders only.


## Personal Data

This project processes privacy-related scenarios.

Do not use or commit real:

- names
- phone numbers
- email addresses
- resident registration numbers
- account identifiers
- breach victim records
- production privacy-policy datasets containing personal information

Use synthetic or properly anonymized fixtures for development and tests.


## Logging

Do not log:

- API keys
- authorization headers
- passwords
- complete environment variables
- unnecessary raw personal data

Prefer structured logs containing technical identifiers and safe metadata.


## Git Safety

Before every commit run:

    git status
    git diff --cached --name-only
    git diff --cached

Verify that:

1. no secret file is staged
2. no credential appears in source code
3. no real personal data is staged
4. generated/local files are not staged accidentally
5. the change matches the intended task


## Ignore Policy

The root .gitignore must protect at least:

- .env and environment variants
- secrets and credentials directories
- private-key formats
- Python virtual environments and caches
- Node dependencies and build output
- local IDE files
- local Claude settings
- generated runtime output


## Tests and Examples

Examples and fixtures must use synthetic data.

Never copy production credentials or real breach records into tests.


## Claude Rules

Claude must not:

- request that real credentials be pasted into source files
- generate hardcoded real secrets
- bypass .gitignore protections
- weaken secret checks for convenience
- commit automatically without reviewing staged changes

If a task requires a secret, Claude should reference an environment
variable and update .env.example with the variable name only.


## Incident Response

If a secret is ever committed:

1. do not merely delete the file in a later commit
2. immediately revoke or rotate the exposed secret
3. stop using the exposed credential
4. assess whether Git history contains the value
5. clean repository history when necessary
6. document the remediation without recording the secret itself
