# Project

What the squad needs to know about this project that is not stack-specific. Read by the Lead, the Devil's
Advocate, Security, the Tester and the Reviewer. Not template-managed: `adopt-template` creates it once
and never overwrites it. A product PR updates it when the change makes an entry untrue
(`.squad/routing.md`, *Scope of a product PR*).

## Security areas

A change that touches one of these is tier `security` (`.squad/routing.md`). Name the concrete types,
files or endpoints.

- <Secrets and tokens: where they are read, stored, compared, logged>
- <Authentication and sessions>
- <File writes and paths derived from external input>
- <Parsing of external input (XML/JSON/YAML, uploads, CLI arguments)>
- <Outbound calls (HTTP clients, TLS, timeouts)>
- <Logging of external data>

## Guarantees

Deliberate behavior that must not change without the Product Manager. Each one is described in
`docs/ARCHITECTURE.md` and, where it was a real choice, has a decision record.

- <guarantee> — [decision NNNN](../docs/decisions/NNNN-title.md)

## Integration surface

What the Reviewer checks when the diff introduces or changes a thing of this kind: every place that must
change with it.

**A new or changed configuration option** touches:
- <the options type / config schema>
- <registration / binding>
- <default config file>
- <the configuration table in `README.md` (key, environment variable, default)>
- <the test that pins the binding>

**A new or changed service / module** touches:
- <its interface>
- <registration and lifetime>
- <the test double in the test project>
- <the component list in `docs/ARCHITECTURE.md`>

**A new external API call or DTO** touches:
- <the client and its DTOs — the external shape must not leak past it>
- <the fake/stub in the tests>

## Test doubles

The hand-written fakes and stubs the tests reuse (no mocking library unless `docs/UNIT_TESTS.md` says
otherwise):

- `<FakeX>` — <what it stands in for>
