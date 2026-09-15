# Weekly DORA Report

## Summary

- Lead Time: null
- Deployment Frequency: null
- MTTR: null
- Change Failure Rate: null
- Deployment Job Failure Rate: null

## Metric Definitions

- Lead Time: time from the code commit to a successful deployment.
- Deployment Frequency: how often deploys happen in a week.
- MTTR: mean time to restore service after an incident.
- Change Failure Rate: failed deployment count / all completed deployment count x 100.
- Deployment Job Failure Rate: share of deployment jobs whose terminal status is failure, error, rollback, or cancellation.

## Data Sources

- Deployment events are sourced from GitHub Pages workflow records and repository JSON files.
- Incident records are sourced only from GitHub Issues with the incident label and repository JSON files.
- If data is missing, values stay null and the reason field explains why.

## Deployment Evidence

- Records: 0
- Unique records: 0
- Duplicate IDs: []
- Status counts: {}

## Incident Evidence

- Incident issues collected: 0
- Resolved incidents: 0

## Collection Errors

- None

## Notes

Empty operational data is intentionally kept as null instead of fabricated values.
