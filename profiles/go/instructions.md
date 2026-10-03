<!-- stack:begin golden-rules -->
- `gofmt` formats everything; `go vet` and **golangci-lint** must report nothing new, and `govulncheck`
  must stay clean.
- Add dependencies with `go get`, run `go mod tidy`, and commit `go.mod` and `go.sum` together.
<!-- stack:end golden-rules -->
<!-- stack:begin commands -->
```bash
go mod download
gofmt -w .
go build ./...
go vet ./...
go test ./... -race -coverprofile=coverage.out
python3 .squad/tools/analyzer-check.py                      # analyzer gate (vet + golangci-lint)
python3 .squad/tools/coverage-check.py                      # coverage gate
```
<!-- stack:end commands -->
<!-- stack:begin configuration -->
- **Go** version and module path from `go.mod`; tools (`govulncheck`) as `tool` dependencies in `go.mod`.
- **golangci-lint** configured in `.golangci.yml`.
<!-- stack:end configuration -->
<!-- stack:begin code-style -->
`gofmt` formatting; short lower-case package names; doc comments on exported identifiers starting with
the identifier's name; errors returned and wrapped with `%w`, never ignored; no `panic` in library code;
`context.Context` first for anything that does I/O or blocks.
<!-- stack:end code-style -->
<!-- stack:begin testing -->
**Unit tests are mandatory for newly written code.** Standard `testing` package, colocated `_test.go`
files, table-driven tests with `t.Run`, `t.Helper()` in helpers, `t.TempDir()` for files, failure messages
that state got and want; no real network or clock.
<!-- stack:end testing -->
