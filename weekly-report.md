# Weekly DORA Report

## Summary

- Lead Time: 31.0 seconds
- Deployment Frequency: 2.00 / week
- MTTR: null
- Change Failure Rate: 0.50

## Metric Definitions

- Lead Time: time from the code commit to a successful deployment.
- Deployment Frequency: how often deploys happen in a week.
- MTTR: mean time to restore service after an incident.
- Change Failure Rate: share of deployments that fail or require rollback.

## Data Sources

- Deployment events are sourced from GitHub Pages workflow records and repository JSON files.
- Incident records are sourced only from GitHub Issues with the incident label and repository JSON files.
- If data is missing, values stay null and the reason field explains why.

## Deployment Evidence

- Records: 4
- Unique records: 4
- Duplicate IDs: []
- Status counts: {'success': 2, 'failure': 2}

## Incident Evidence

- Incident issues collected: 0
- Resolved incidents: 0

## Collection Errors

- None

## Notes

Empty operational data is intentionally kept as null instead of fabricated values.
