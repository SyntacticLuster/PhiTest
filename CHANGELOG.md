# Changelog

All notable changes to ɸTest will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- Six experimental protocols: `partition_sensitivity`, `global_availability`, `metacognitive_calibration`, `self_model_continuity`, `phenomenal_report_consistency`, `perturbation_response`
- Four theory families: integration, global_availability, metacognition, self_model
- SQLite persistence with append-only immutability triggers and foreign key enforcement
- SHA-256 audit chain with tamper detection
- `ManualTarget` and `HTTPJsonTarget` adapters
- FastAPI application with HTML dashboard, experiment management, run execution, and report views
- Report generation with enforced epistemic boundary statement
- Six evidence claim types enforced in schema: `observation`, `operational_metric`, `theory_prediction`, `inference`, `self_report`, `unresolved`
- Environment-based configuration (`PHITEST_DB_PATH`, `PHITEST_TARGET_TOKEN`, `PHITEST_MAX_OBSERVATION_LENGTH`)
- 47-test pytest suite
- Apache-2.0 license
- Public repository surface: README, CONTRIBUTING, SECURITY, SUPPORT, GOVERNANCE
