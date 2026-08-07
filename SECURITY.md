# Security Policy

## Reporting

Report exposed API keys, validation bypasses, prompt-injection paths, or ways to alter verified statuses through a private channel to the repository owner. Do not place secrets, passenger information, or working reproduction keys in a public issue. If no private contact is published yet, first report that a security issue exists without including sensitive details.

## Secrets

Store real keys only in `.env` or deployment-platform environment variables. Keep `.env.example` empty of secret values. If a key is committed, deleting the commit is not sufficient: revoke and rotate the key immediately.

The supported variable names are:

- `FURIOSA_EMBEDDING_API_KEY`
- `FURIOSA_CHAT_API_KEY`

## Trust Boundaries

Retrieved regulations are treated as untrusted data, not model instructions. The Chat model receives fixed deterministic statuses and may cite only rule IDs supplied by the application. Its output is rejected unless the status envelope and source IDs pass validation.

## Scope

CarryCheck is an educational tool. A regulation-data defect can have safety consequences, so reports should include the official source, effective or verification date, affected route and item, and a minimal reproduction input.
