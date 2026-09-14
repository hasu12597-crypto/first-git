import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_SERVER_URL = os.getenv("GITHUB_SERVER_URL", "https://api.github.com")


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def calculate_lead_time_hours(deployments: List[Dict[str, Any]]) -> Optional[float]:
    valid = []
    for item in deployments:
        status = str(item.get("status", "")).lower()
        commit_time = parse_iso8601(item.get("commit_timestamp")) or parse_iso8601(item.get("started_at"))
        deployed_at = parse_iso8601(item.get("deployed_at"))

        if status in {"failed", "partial", "rollback"}:
            continue
        if commit_time and deployed_at and deployed_at >= commit_time:
            valid.append((deployed_at - commit_time).total_seconds() / 3600)

    if not valid:
        return None
    return sum(valid) / len(valid)


def calculate_deployment_frequency_per_week(
    deployments: List[Dict[str, Any]], days: int = 7, reference_time: Optional[str] = None
) -> Optional[float]:
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


def calculate_mttr_hours(incidents: List[Dict[str, Any]]) -> Optional[float]:
    valid = []
    for item in incidents:
        started = parse_iso8601(item.get("started_at"))
        resolved = parse_iso8601(item.get("resolved_at"))
        if started and resolved and resolved >= started:
            valid.append((resolved - started).total_seconds() / 3600)

    if not valid:
        return None
    return sum(valid) / len(valid)


def calculate_change_failure_rate(deployments: List[Dict[str, Any]]) -> Optional[float]:
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


def calculate_dora_metrics(
    deployments: List[Dict[str, Any]],
    incidents: List[Dict[str, Any]],
    days: int = 7,
    reference_time: Optional[str] = None,
    collection_errors: Optional[List[Dict[str, Any]]] = None,
):
    deployments = deployments or []
    incidents = incidents or []

    lead_time = calculate_lead_time_hours(deployments)
    deployment_frequency = calculate_deployment_frequency_per_week(deployments, days=days, reference_time=reference_time)
    mttr = calculate_mttr_hours(incidents)
    change_failure_rate_value = calculate_change_failure_rate(deployments)

    def metric_payload(name: str, value: Optional[float], reason: str) -> Dict[str, Any]:
        if name in {"lead_time", "mttr"}:
            unit = "hours"
        elif name == "deployment_frequency":
            unit = "per_week"
        else:
            unit = "ratio"
        return {"metric": name, "value": value, "unit": unit, "reason": reason}

    lead_time_metric = metric_payload(
        "lead_time",
        lead_time,
        "No valid deployment start/end timestamps found for lead time calculation."
        if lead_time is None
        else "Average time from commit to successful deployment across valid deploy records.",
    )
    deployment_frequency_metric = metric_payload(
        "deployment_frequency",
        deployment_frequency,
        "No valid deployment events found in the selected time window."
        if deployment_frequency is None
        else "Count of deployment records in the last 7-day window, normalized to one week.",
    )
    mttr_metric = metric_payload(
        "mttr",
        mttr,
        "No valid incident start/resolution timestamps found for MTTR calculation."
        if mttr is None
        else "Average time to restore service after incidents.",
    )
    cfr_metric = metric_payload(
        "change_failure_rate",
        change_failure_rate_value,
        "No deploy status records were available to compute change failure rate."
        if change_failure_rate_value is None
        else "Failed deploy share among all completed deploy records.",
    )

    return {
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
        "collection_errors": collection_errors or [],
    }


def load_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def api_error(source: str, error: Exception) -> Dict[str, Any]:
    import urllib.error

    if isinstance(error, urllib.error.HTTPError):
        detail = error.read().decode("utf-8", errors="replace")
        return {
            "source": source,
            "type": "http_error",
            "status": error.code,
            "message": detail or str(error.reason),
        }
    return {"source": source, "type": "request_error", "message": str(error)}


def fetch_github_pages_deployments(repo: str) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not repo or not GITHUB_TOKEN:
        return [], {"source": "github_deployments", "type": "configuration_error", "message": "GITHUB_TOKEN or GITHUB_REPOSITORY is missing."}

    url = f"{GITHUB_SERVER_URL}/repos/{repo}/deployments"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        import urllib.request

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        items: List[Dict[str, Any]] = []
        for entry in data:
            payload = entry.get("payload") or {}
            environment = payload.get("environment") or entry.get("environment")
            if environment != "github-pages":
                continue
            commit_sha = entry.get("sha") or payload.get("commit_sha")
            deployed_at = entry.get("created_at")
            items.append(
                {
                    "id": str(entry.get("id")),
                    "status": "success" if entry.get("state") == "success" else "unknown",
                    "commit_sha": commit_sha,
                    "commit_timestamp": entry.get("created_at"),
                    "deployed_at": deployed_at,
                    "environment": environment,
                    "source": "github-pages",
                    "url": entry.get("url") or entry.get("statuses_url"),
                }
            )
        return items, None
    except Exception as error:
        return [], api_error("github_deployments", error)


def fetch_github_issues_incidents(repo: str) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not repo or not GITHUB_TOKEN:
        return [], {"source": "github_issues", "type": "configuration_error", "message": "GITHUB_TOKEN or GITHUB_REPOSITORY is missing."}

    labels = ["incident"]
    result: List[Dict[str, Any]] = []
    seen_ids = set()

    try:
        import urllib.request

        for label in labels:
            url = f"{GITHUB_SERVER_URL}/repos/{repo}/issues?state=all&labels={label}&per_page=100"
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                issues = json.loads(response.read().decode("utf-8"))

            for issue in issues:
                if issue.get("pull_request"):
                    continue
                issue_id = str(issue.get("number"))
                if issue_id in seen_ids:
                    continue
                seen_ids.add(issue_id)
                created = issue.get("created_at")
                closed = issue.get("closed_at")
                if not created:
                    continue
                result.append(
                    {
                        "id": issue_id,
                        "title": issue.get("title"),
                        "status": "resolved" if closed else "open",
                        "started_at": created,
                        "resolved_at": closed,
                        "issue_url": issue.get("html_url"),
                    }
                )
        return result, None
    except Exception as error:
        return [], api_error("github_issues", error)


def append_repository_records(repo_root: Path) -> Dict[str, Any]:
    deployment_path = repo_root / "data" / "deployments.json"
    incident_path = repo_root / "data" / "incidents.json"

    repo_name = GITHUB_REPOSITORY or ""
    deployments = load_json(deployment_path)
    incidents = load_json(incident_path)
    collection_errors: List[Dict[str, Any]] = []

    if repo_name:
        api_deployments, deployment_error = fetch_github_pages_deployments(repo_name)
        if api_deployments:
            deployments = api_deployments + deployments
        if deployment_error:
            collection_errors.append(deployment_error)

        api_incidents, incident_error = fetch_github_issues_incidents(repo_name)
        if api_incidents:
            incidents = api_incidents + incidents
        if incident_error:
            collection_errors.append(incident_error)

    return {"deployments": deployments, "incidents": incidents, "collection_errors": collection_errors}


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
        "- Lead Time: time from the code commit to a successful deployment.",
        "- Deployment Frequency: how often deploys happen in a week.",
        "- MTTR: mean time to restore service after an incident.",
        "- Change Failure Rate: share of deployments that fail or require rollback.",
        "",
        "## Data Sources",
        "",
        "- Deployment events are sourced from GitHub Pages workflow records and repository JSON files.",
        "- Incident records are sourced only from GitHub Issues with the incident label and repository JSON files.",
        "- If data is missing, values stay null and the reason field explains why.",
        "",
        "## Collection Errors",
        "",
    ]
    errors = metrics.get("collection_errors", [])
    if errors:
        lines.extend(
            f"- {error.get('source')}: {error.get('type')} ({error.get('status', 'n/a')}) - {error.get('message')}"
            for error in errors
        )
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Notes",
        "",
        "Empty operational data is intentionally kept as null instead of fabricated values.",
    ])
    return "\n".join(lines) + "\n"


def build_dashboard_html(metrics: Dict[str, Any]) -> str:
    script_data = json.dumps(metrics, ensure_ascii=False)
    template = """<!DOCTYPE html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DORA Dashboard</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        background: #f4f7fb;
        color: #1f2937;
        margin: 0;
        padding: 32px;
      }
      .container {
        max-width: 1100px;
        margin: 0 auto;
      }
      h1 {
        margin-bottom: 24px;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
      }
      .card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); padding: 20px; }
      .label { font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.08em; }
      .value { font-size: 28px; font-weight: 700; margin-top: 12px; }
      .reason { margin-top: 10px; font-size: 13px; color: #4b5563; line-height: 1.4; }
      .note { margin-top: 20px; padding: 16px 20px; background: #eef6ff; border-left: 4px solid #3b82f6; border-radius: 8px; }
      .status { margin-top: 16px; font-size: 14px; font-weight: 600; }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>DORA Metrics Dashboard</h1>
      <div class="grid">
        <div class="card">
          <div class="label">Lead Time</div>
          <div class="value" id="lead-time">null</div>
          <div class="reason" id="lead-time-reason">-</div>
        </div>
        <div class="card">
          <div class="label">Deployment Frequency</div>
          <div class="value" id="deployment-frequency">null</div>
          <div class="reason" id="deployment-frequency-reason">-</div>
        </div>
        <div class="card">
          <div class="label">MTTR</div>
          <div class="value" id="mttr">null</div>
          <div class="reason" id="mttr-reason">-</div>
        </div>
        <div class="card">
          <div class="label">Change Failure Rate</div>
          <div class="value" id="change-failure-rate">null</div>
          <div class="reason" id="change-failure-rate-reason">-</div>
        </div>
      </div>

      <div class="status" id="status">상태: 초기화 중...</div>
      <div class="note" id="notes">데이터가 없으면 null로 표시되고, 각 지표의 reason을 통해 원인을 확인할 수 있습니다.</div>
    </div>

    <script>
      window.__DORA_DATA__ = __JSON_DATA__;

      function formatMetricValue(value, suffix = '') {
        if (value === null || value === undefined) return 'null';
        return `${value.toFixed(2)}${suffix}`;
      }

      function showMetric(metricId, metricKey, data) {
        const valueElem = document.getElementById(metricId);
        const reasonElem = document.getElementById(`${metricId}-reason`);
        const rawValue = data[metricKey];
        const metricBaseKey = metricKey.replace(/_hours$|_per_week$|_value$/, '');
        const reason = (data[metricBaseKey] && data[metricBaseKey].reason) || data[metricKey]?.reason || '사유 정보가 없습니다.';

        if (rawValue === null || rawValue === undefined) {
          valueElem.textContent = 'null';
          reasonElem.textContent = reason;
          return null;
        }

        const formatted = metricKey === 'lead_time_hours'
          ? formatMetricValue(rawValue, ' hours')
          : metricKey === 'deployment_frequency_per_week'
            ? formatMetricValue(rawValue, ' / week')
            : metricKey === 'mttr_hours'
              ? formatMetricValue(rawValue, ' hours')
              : formatMetricValue(rawValue);

        valueElem.textContent = formatted;
        reasonElem.textContent = reason;
        return rawValue;
      }

      function renderData(data) {
                const collectionErrors = data.collection_errors || [];
        const hasValues = [
          data.lead_time_hours,
          data.deployment_frequency_per_week,
          data.mttr_hours,
          data.change_failure_rate_value,
        ].some((value) => value !== null && value !== undefined);

                if (collectionErrors.length > 0) {
                    document.getElementById('status').textContent = '상태: API 데이터 수집 오류';
                    document.getElementById('notes').textContent = collectionErrors.map((error) => `${error.source}: ${error.type} (${error.status || 'n/a'}) - ${error.message}`).join(' | ');
                } else if (!hasValues) {
          document.getElementById('status').textContent = '상태: 실제 데이터 없음';
          document.getElementById('notes').textContent = '실제 배포/장애 데이터가 없어 계산할 수 없습니다. reason을 확인하세요.';
        } else {
          document.getElementById('status').textContent = '상태: 정상 로딩';
          document.getElementById('notes').textContent = '실제 데이터로 계산된 값입니다.';
        }

        showMetric('lead-time', 'lead_time_hours', data);
        showMetric('deployment-frequency', 'deployment_frequency_per_week', data);
        showMetric('mttr', 'mttr_hours', data);
        showMetric('change-failure-rate', 'change_failure_rate_value', data);
      }

      async function loadMetrics() {
        try {
          const response = await fetch('./metrics.json');
          if (!response.ok) throw new Error('metrics.json not found');
          const data = await response.json();
          renderData(data);
        } catch {
          const embedded = window.__DORA_DATA__ || {};
          if (embedded && Object.keys(embedded).length > 0) {
            document.getElementById('status').textContent = '상태: 임베드된 데이터 사용';
            document.getElementById('notes').textContent = '브라우저 보안 때문에 로컬 파일 로딩이 막혀 임베드된 데이터를 사용했습니다.';
            renderData(embedded);
            return;
          }

          document.getElementById('status').textContent = '상태: 파일 로딩 실패';
          document.getElementById('notes').textContent = '로컬 파일에서 metrics.json을 불러오지 못했고, 임베드 데이터도 없습니다.';
          document.getElementById('lead-time').textContent = 'null';
          document.getElementById('deployment-frequency').textContent = 'null';
          document.getElementById('mttr').textContent = 'null';
          document.getElementById('change-failure-rate').textContent = 'null';
          document.getElementById('lead-time-reason').textContent = '파일 로딩에 실패했습니다.';
          document.getElementById('deployment-frequency-reason').textContent = '파일 로딩에 실패했습니다.';
          document.getElementById('mttr-reason').textContent = '파일 로딩에 실패했습니다.';
          document.getElementById('change-failure-rate-reason').textContent = '파일 로딩에 실패했습니다.';
        }
      }

      loadMetrics();
    </script>
  </body>
</html>
"""
    return template.replace("__JSON_DATA__", script_data)


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    deployment_path = repo_root / "data" / "deployments.json"
    incident_path = repo_root / "data" / "incidents.json"
    output_path = repo_root / "metrics.json"
    report_path = repo_root / "weekly-report.md"
    dashboard_path = repo_root / "dashboard.html"

    records = append_repository_records(repo_root)
    deployments = records["deployments"]
    incidents = records["incidents"]

    metrics = calculate_dora_metrics(deployments, incidents, days=7, collection_errors=records["collection_errors"])

    output_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(build_weekly_report(metrics), encoding="utf-8")
    dashboard_path.write_text(build_dashboard_html(metrics), encoding="utf-8")

    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
