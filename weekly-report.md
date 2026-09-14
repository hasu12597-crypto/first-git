# Weekly DORA Report

## Summary

- Lead Time: null
- Deployment Frequency: null
- MTTR: null
- Change Failure Rate: null

## Metric Definitions

- Lead Time: time from the code commit to a successful deployment.
- Deployment Frequency: how often deploys happen in a week.
- MTTR: mean time to restore service after an incident.
- Change Failure Rate: share of deployments that fail or require rollback.

## Data Sources

- Deployment events are sourced from GitHub Pages workflow records and repository JSON files.
- Incident records are sourced only from GitHub Issues with the incident label and repository JSON files.
- If data is missing, values stay null and the reason field explains why.

## Collection Errors

- None

## Notes

Empty operational data is intentionally kept as null instead of fabricated values.
