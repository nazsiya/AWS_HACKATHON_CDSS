# CDSS Prototype — Performance Benchmark (1 slide)

**Environment:** Local → SSH tunnel → Aurora (ap-south-1) · **Target:** &lt;2s · **Date:** 2026-03-08

### Benchmark results

| Endpoint | Avg latency | vs target |
|----------|-------------|-----------|
| GET /health | 2.80s | Fail |
| GET /api/v1/patients | 5.78s | Fail |
| GET /api/v1/patients/PT-1001 | 10.18s | Fail |
| GET /api/v1/terminology | 2.56s | Fail |

### Bottlenecks

| # | Cause | Impact |
|---|--------|--------|
| 1 | SSH tunnel + cross-region RTT | ~0.5–1s per request |
| 2 | Synchronous Bedrock summary (patient detail) | ~5–8s |
| 3 | Cold terminology I/O | First hits ~2.5s |

### Production expectation

| Path | Environment | Expected latency |
|------|-------------|------------------|
| DB (health, patients list) | Lambda + Aurora in VPC (same region) | &lt;100ms |
| Patient detail + Bedrock | Async or cached | &lt;2s end-to-end |
| Terminology | CloudFront / ElastiCache | &lt;50ms |

### Summary

| Metric | Local (measured) | Production (expected) |
|--------|------------------|------------------------|
| Target | &lt;2s | &lt;2s |
| All endpoints | Fail (2.6–10.2s) | Meet (tunnel/LLM removed) |

### Additional details

| Item | Detail |
|------|--------|
| Tuning done | Connection pooling enabled to reduce DB handshakes |
| CI recommendation | Run benchmarks from AWS (e.g. CodeBuild) in ap-south-1 for production-like metrics |
| Req reference | Req 6.3 (performance benchmarking) |

### Future development

| Area | Planned change | Outcome |
|------|----------------|--------|
| Bedrock on patient detail | Async pattern (WebSocket/polling + “Generating…” in UI) | Sub-2s perceived latency; LLM off critical path |
| Benchmark runner | Move to in-region (CodeBuild/Lambda) | Accurate prod latency; no tunnel bias |
| Terminology | CloudFront or ElastiCache in front of API | &lt;50ms repeat hits |
| SLO & monitoring | 99.5% uptime target; alarms + runbooks (Phase 6) | Production readiness |
| Critical-path tests | RBAC + performance in CI | Regressions caught before deploy |

