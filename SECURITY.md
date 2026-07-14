# Security Policy

## Supported Versions

This repository currently supports security fixes only for the latest public
state of the project.

| Version | Supported |
| --- | --- |
| Latest public branch / latest public release | Yes |
| Older releases and historical branches | No |

## Reporting a Vulnerability

Please do not open a public issue for a suspected security problem.

Preferred path:

1. Use GitHub private vulnerability reporting for this repository if it is enabled.
2. If private reporting is not enabled, contact the maintainer directly through
   GitHub before any public disclosure.

Please include as much of the following as you can:

- affected commit, branch, or release
- steps to reproduce
- impact and expected risk
- whether the issue requires authentication, local access, or special configuration
- any suggested mitigation if you already found one

## Response Expectations

- Initial triage target: within 7 days
- If the issue is confirmed, a mitigation plan or fix status update should follow
  as soon as reasonably possible

## Scope Notes

This project is a local-first demo application. The highest-priority reports are
issues that could expose secrets, execute unintended commands, leak local files,
or create unsafe defaults in the public demo workflow.
