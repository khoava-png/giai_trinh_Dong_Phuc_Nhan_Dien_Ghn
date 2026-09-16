# Sheets-Centric Architecture (ORDER-ARCH-V3)

## Executive Summary
This document establishes the architecture for migrating computation, scheduling, and notifications out of the Python backend and into Google Sheets and Apps Script, transforming Python into a pure data collector.

## Architectural Boundaries
1. **Python Collector**: Login, raw scraping, source validation, full snapshot replacement to `01_RAW_CHI_TIET`, health check endpoints.
2. **Google Sheets Compute**: Data cleansing, mapping (`02_CO_CAU`), enrichment (`03_DATA_ENRICHED`), and reporting aggregations (`04_RP_AM`, `05_RP_VUNG`) via native formulas.
3. **Apps Script Scheduler & Engine**: Clock trigger execution, configuration management (`00_CONFIG`), idempotency checks (`07_SEND_LOG`), queue management (`06_SEND_QUEUE`), and GTalk message dispatch (`DRY_RUN = true`).
4. **Frontend**: Read-only presentation layer reading strictly from aggregated tabs and `08_SYSTEM_STATE`.
