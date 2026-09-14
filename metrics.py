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
      .card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        padding: 20px;
      }
      .label {
        font-size: 12px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .value {
        font-size: 28px;
        font-weight: 700;
        margin-top: 12px;
      }
      .reason {
        margin-top: 10px;
        font-size: 13px;
        color: #4b5563;
        line-height: 1.4;
      }
      .note {
        margin-top: 20px;
        padding: 16px 20px;
        background: #eef6ff;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
      }
      .status {
        margin-top: 16px;
        font-size: 14px;
        font-weight: 600;
      }
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
      <div class="note" id="notes">
        데이터가 아직 없으면 null로 표시되고, 값이 없는 이유는 각 지표의 reason을 확인하세요.
      </div>
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
          reasonElem.textContent = reason || '데이터가 아직 준비되지 않았습니다.';
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
        reasonElem.textContent = reason || '계산 가능한 데이터가 있습니다.';
        return rawValue;
      }

      function showNoDataState(data) {
        document.getElementById('status').textContent = '상태: 실제 데이터 없음';
        document.getElementById('notes').textContent = '실제 배포/장애 데이터가 없어 계산할 수 없습니다. 아래 reason을 확인하세요.';
        showMetric('lead-time', 'lead_time_hours', data);
        showMetric('deployment-frequency', 'deployment_frequency_per_week', data);
        showMetric('mttr', 'mttr_hours', data);
        showMetric('change-failure-rate', 'change_failure_rate_value', data);
      }

      function showLoadErrorState() {
        document.getElementById('status').textContent = '상태: 파일 로딩 실패';
        document.getElementById('notes').textContent = '브라우저 보안 때문에 로컬 파일에서 metrics.json을 불러오지 못했습니다. 임베드된 데이터로 표시합니다.';
        const embedded = window.__DORA_DATA__ || {};
        if (embedded && Object.keys(embedded).length > 0) {
          showNoDataState(embedded);
          return;
        }
        document.getElementById('lead-time').textContent = 'null';
        document.getElementById('deployment-frequency').textContent = 'null';
        document.getElementById('mttr').textContent = 'null';
        document.getElementById('change-failure-rate').textContent = 'null';
        document.getElementById('lead-time-reason').textContent = '파일 로딩에 실패했습니다.';
        document.getElementById('deployment-frequency-reason').textContent = '파일 로딩에 실패했습니다.';
        document.getElementById('mttr-reason').textContent = '파일 로딩에 실패했습니다.';
        document.getElementById('change-failure-rate-reason').textContent = '파일 로딩에 실패했습니다.';
      }

      async function loadMetrics() {
        try {
          const response = await fetch('./metrics.json');
          if (!response.ok) throw new Error('metrics.json not found');
          const data = await response.json();
          const hasValues = [
            data.lead_time_hours,
            data.deployment_frequency_per_week,
            data.mttr_hours,
            data.change_failure_rate_value,
          ].some((value) => value !== null && value !== undefined);

          if (!hasValues) {
            document.getElementById('status').textContent = '상태: 실제 데이터 없음';
            showNoDataState(data);
            return;
          }

          document.getElementById('status').textContent = '상태: 정상 로딩';
          document.getElementById('notes').textContent = '파일에서 데이터를 정상적으로 불러왔습니다.';
          showMetric('lead-time', 'lead_time_hours', data);
          showMetric('deployment-frequency', 'deployment_frequency_per_week', data);
          showMetric('mttr', 'mttr_hours', data);
          showMetric('change-failure-rate', 'change_failure_rate_value', data);
        } catch (error) {
          const embedded = window.__DORA_DATA__ || {};
          if (embedded && Object.keys(embedded).length > 0) {
            const hasValues = [
              embedded.lead_time_hours,
              embedded.deployment_frequency_per_week,
              embedded.mttr_hours,
              embedded.change_failure_rate_value,
            ].some((value) => value !== null && value !== undefined);

            if (!hasValues) {
              showNoDataState(embedded);
              return;
            }

            document.getElementById('status').textContent = '상태: 임베드된 데이터 사용';
            document.getElementById('notes').textContent = '파일 로딩이 차단되어 임베드된 데이터를 사용했습니다.';
            showMetric('lead-time', 'lead_time_hours', embedded);
            showMetric('deployment-frequency', 'deployment_frequency_per_week', embedded);
            showMetric('mttr', 'mttr_hours', embedded);
            showMetric('change-failure-rate', 'change_failure_rate_value', embedded);
            return;
          }

          showLoadErrorState();
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

    deployments = load_json(deployment_path)
    incidents = load_json(incident_path)

    metrics = calculate_dora_metrics(deployments, incidents, days=7)

    output_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(build_weekly_report(metrics), encoding="utf-8")
    dashboard_path.write_text(build_dashboard_html(metrics), encoding="utf-8")

    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
