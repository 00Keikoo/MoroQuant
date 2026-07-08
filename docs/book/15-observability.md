# 15 - Observability Standards

Guidelines for logging formatting, custom metric exports, and trace propagation.

## Logging Format

All application logs exported from MoroQuant services must adhere to this structured format:

```json
{
  "timestamp": "ISO8601 UTC String",
  "level": "INFO / WARN / ERROR / DEBUG",
  "service": "Service Identifier",
  "trace_id": "Optional unique request trace id",
  "message": "Human-readable context details",
  "extra": {}
}
```

## Telemetry Metrics Matrix

| Metric Name | Type | Target | Indicator |
|---|---|---|---|
| `http_requests_total` | Counter | API | Volume |
| `http_request_duration_seconds` | Histogram | API | Latency |
| `active_positions` | Gauge | Execution | Portfolio State |
| `order_slippage_pct` | Histogram | Execution | Execution Quality |

## Observability Best Practices
- **Never Log Secrets**: Exclude credentials, passwords, auth tokens, or private customer keys from log lines.
- **Trace Context Propagation**: Propagate telemetry contexts across network requests to create end-to-end trace flows.
- **Metric Labeling**: Use key tags (e.g. `symbol`, `status_code`) rather than generating dynamic metric names, which results in metric name bloat.

## Observability Checklist
- [ ] Log output is written to standard output (`stdout`) in JSON formatting.
- [ ] Error objects include error class and stack trace details.
- [ ] Application services export metrics via a `/metrics` route for Prometheus scraping.
