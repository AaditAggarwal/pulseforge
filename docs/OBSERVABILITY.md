# OBSERVABILITY

## Decided now, because it cannot be retrofitted

Structured JSON logging from the first line of code, with a correlation ID threaded through every
request. Retrofitting correlation IDs into an async system afterwards means touching every call site,
and it does not get done.

Every log line carries: timestamp, level, event name, correlation ID, component. Messages are event
names, not sentences, so they can be filtered.

## Status

Logging foundation lands in Phase 00 Task 4. Metrics and traces are Phase 12 and are not designed yet.

## Reading it during an incident

Written in Phase 12 against real logs from real runs. Writing it before then would be fiction.
