# Quota Budget & Headroom Analysis

## Google Sheets & Apps Script Quotas
- **UrlFetch Calls**: Limit 20,000 / day (Consumer) or 100,000 / day (Workspace). Estimated usage: ~500 calls/day. Headroom: **95%**.
- **Trigger Runtime**: Limit 30 min / execution (Consumer) or 6 min / execution (Workspace). Estimated execution time per tick: ~2.5 seconds. Headroom: **99%**.
- **Sheet Read/Write Operations**: Limit 60 requests / minute per user. Batch reads/writes implemented via `getValues()` / `setValues()`. Headroom: **90%**.
- **Python API Calls**: Reduced by 80% (no heavy Pandas aggregations or schedule checks running on server).
