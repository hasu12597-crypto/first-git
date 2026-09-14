# Weekly DORA Report

## Summary

- Lead Time: null
- Deployment Frequency: null
- MTTR: null
- Change Failure Rate: null

## Metric Definitions

- Lead Time: time from the start of work to successful deployment.
- Deployment Frequency: how often deploys happen in a week.
- MTTR: mean time to restore service after an incident.
- Change Failure Rate: share of deployments that fail or require rollback.

## Data Sources

- Deployment events are sourced from deployment records in the repository or workflow outputs.
- Incident records are sourced from operational incident logs or manually maintained JSON files.
- If no relevant records exist, values stay null and include the reason field.

## Notes

This repository currently includes a workflow scaffold and sample files for DORA collection. Actual deployment and incident records must be populated before the metrics become meaningful.
