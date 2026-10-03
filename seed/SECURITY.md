# Security Policy

## Supported Versions

Only the latest release receives security fixes.

| Version | Supported |
| ------- | --------- |
| latest  | Yes       |
| older   | No        |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report vulnerabilities by e-mail to:

**{{TODO: security contact e-mail}}**

Include in your report:

- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

You will receive an acknowledgement within **5 business days**. We aim to release a fix or mitigation
within **30 days** for confirmed vulnerabilities. We will keep you informed of progress throughout the
process.

## Deployment Security Considerations

{{TODO: How the software is meant to be deployed (e.g. home network, behind a reverse proxy), and what an
operator must do before exposing it: authentication, secrets in environment variables, minimum
permissions, network restrictions.}}

## Scope

The following are considered in scope for vulnerability reports:

- {{TODO: The project's attack surface — the same areas as *Security areas* in `.squad/project.md`.}}
- Dependency vulnerabilities in packages consumed by the project

The following are **out of scope**:

- Attacks that require local system access or physical access to the host
- Issues arising from misconfiguration of the deployment environment
