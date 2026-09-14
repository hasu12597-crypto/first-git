import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def isoformat_utc(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def calculate_lead_time_hours(deployments: List[Dict[str, Any]]) -> float:
    valid = []
    for item in deployments:
        status = str(item.get("status", "")).lower()
        started = parse_iso8601(item.get("started_at"))
        deployed = parse_iso8601(item.get("deployed_at"))

        if status in {"failed", "partial", "rollback"}:
            continue
        if started and deployed and deployed >= started:
            valid.append((deployed - started).total_seconds() / 3600)

    if not valid:
        return None
    return sum(valid) / len(valid)


def calculate_deployment_frequency_per_week(deployments: List[Dict[str, Any]], days: int = 7, reference_time: Optional[str] = None) -> float:
    if not deployments:
        return None

    if reference_time is None:
        reference_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = parse_iso8601(reference_time)
    if end is None:
        return None
    start = end - timedelta(days=days)

    count = 0
    for item in deployments:
        deployed_at = parse_iso8601(item.get("deployed_at"))
        if deployed_at and start <= deployed_at <= end:
            count += 1

    if count == 0:
        return 0.0
    return count / (days / 7)


def calculate_mttr_hours(incidents: List[Dict[str, Any]]) -> float:
    valid = []
    for item in incidents:
        started = parse_iso8601(item.get("started_at"))
        resolved = parse_iso8601(item.get("resolved_at"))
        if started and resolved and resolved >= started:
            valid.append((resolved - started).total_seconds() / 3600)

    if not valid:
        return None
    return sum(valid) / len(valid)


def calculate_change_failure_rate(deployments: List[Dict[str, Any]]) -> float:
    if not deployments:
        return None
    total = 0
    failed = 0
    for item in deployments:
        status = str(item.get("status", "")).lower()
        if status in {"success", "failed", "partial", "rollback"}:
            total += 1
            if status in {"failed", "partial", "rollback"}:
                failed += 1

    if total == 0:
        return None
    return failed / total


def calculate_dora_metrics(deployments: List[Dict[str, Any]], incidents: List[Dict[str, Any]], days: int = 7, reference_time: Optional[str] = None):
    deployments = deployments or []
    incidents = incidents or []

    lead_time = calculate_lead_time_hours(deployments)
    deployment_frequency = calculate_deployment_frequency_per_week(deployments, days=days, reference_time=reference_time)
    mttr = calculate_mttr_hours(incidents)
    change_failure_rate_value = calculate_change_failure_rate(deployments)

    def metric_payload(name: str, value: Optional[float], reason: str) -> Dict[str, Any]:
        return {
            "metric": name,
            "value": value,
            "unit": "hours" if name in {"lead_time", "mttr"} else "per_week" if name == "deployment_frequency" else "ratio",
            "reason": reason,
        }

    lead_time_metric = metric_payload(
        "lead_time",
        lead_time,
        "No valid deployment start/end timestamps found for lead time calculation." if lead_time is None else "Average time from code start to successful deployment across valid deploy records."
    )
    deployment_frequency_metric = metric_payload(
        "deployment_frequency",
        deployment_frequency,
        "No valid deployment events found in the selected time window." if deployment_frequency is None else "Count of deployment records in the last 7-day window, normalized to one week."
    )
    mttr_metric = metric_payload(
        "mttr",
        mttr,
        "No valid incident start/resolution timestamps found for MTTR calculation." if mttr is None else "Average time to restore service after incidents."
    )
    cfr_metric = metric_payload(
        "change_failure_rate",
        change_failure_rate_value,
        "No deploy status records were available to compute change failure rate." if change_failure_rate_value is None else "Failed deploy share among all completed deploy records."
    )

    metrics = {
        "lead_time": lead_time_metric,
        "deployment_frequency": deployment_frequency_metric,
        "mttr": mttr_metric,
        "change_failure_rate": cfr_metric,
        "lead_time_hours": lead_time,
        "deployment_frequency_per_week": deployment_frequency,
        "mttr_hours": mttr,
        "change_failure_rate_value": change_failure_rate_value,
        "window_days": days,
        "reference_time": reference_time or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return metrics


def load_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        return []


def build_weekly_report(metrics: Dict[str, Any]) -> str:
    def format_value(value: Optional[float], suffix: str = "") -> str:
        if value is None:
            return "null"
        return f"{value:.2f}{suffix}"

    lines = [
        "# Weekly DORA Report",
        "",
        "## Summary",
        "",
        f"- Lead Time: {format_value(metrics.get('lead_time_hours'), ' hours')}",
        f"- Deployment Frequency: {format_value(metrics.get('deployment_frequency_per_week'), ' / week')}",
        f"- MTTR: {format_value(metrics.get('mttr_hours'), ' hours')}",
        f"- Change Failure Rate: {format_value(metrics.get('change_failure_rate_value'))}",
        "",
        "## Metric Definitions",
        "",
        "- Lead Time: time from the start of work to successful deployment.",
        "- Deployment Frequency: how often deploys happen in a week.",
        "- MTTR: mean time to restore service after an incident.",
        "- Change Failure Rate: share of deployments that fail or require rollback.",
        "",
        "## Data Sources",
        "",
        "- Deployment events are sourced from deployment records in the repository or workflow outputs.",
        "- Incident records are sourced from operational incident logs or manually maintained JSON files.",
        "- If no relevant records exist, values stay null and include the reason field.",
        "",
        "## Notes",
        "",
        "This repository currently includes a workflow scaffold and sample files for DORA collection. Actual deployment and incident records must be populated before the metrics become meaningful.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    deployment_path = repo_root / "data" / "deployments.json"
    incident_path = repo_root / "data" / "incidents.json"
    output_path = repo_root / "metrics.json"
    report_path = repo_root / "weekly-report.md"

    deployments = load_json(deployment_path)
    incidents = load_json(incident_path)

    metrics = calculate_dora_metrics(deployments, incidents, days=7)

    output_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(build_weekly_report(metrics), encoding="utf-8")

    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
