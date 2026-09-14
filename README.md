# first-git

Git과 GitHub 실습용 저장소입니다. 이 저장소는 GitHub Actions를 이용해 DORA 4대 지표를 자동 수집하고, JSON 아티팩트와 주간 보고서를 생성하는 예제를 제공합니다.

## 목차

- DORA 4대 지표 정의
- 데이터 출처와 기록 방법
- 저장소 구조
- 로컬 실행 방법
- GitHub Actions 실행 방법
- null 처리 규칙
- 대시보드 설명
- 현재 구현 상태와 남은 과제

## DORA 4대 지표 정의

### 1) Lead Time
- 정의: 코드가 시작된 시점부터 실제 운영 환경에 배포되기까지 걸리는 시간입니다.
- 의미: 변경이 얼마나 빠르게 고객에게 전달되는지를 보여줍니다.
- 데이터 출처: `data/deployments.json`의 `started_at`과 `deployed_at` 값을 사용합니다.
- 계산 방식: 유효한 배포 pair의 평균 시간(시간 단위)입니다.

### 2) Deployment Frequency
- 정의: 일정 기간(기본 7일) 동안 몇 번 배포가 발생했는지를 나타냅니다.
- 의미: 팀의 배포 속도와 릴리즈 주기를 보여줍니다.
- 데이터 출처: `data/deployments.json`의 `deployed_at` 값을 기준으로 집계합니다.
- 계산 방식: 7일 기준 배포 횟수의 비율로 계산합니다.

### 3) MTTR (Mean Time To Recovery)
- 정의: 장애 발생 시점부터 복구 완료 시점까지의 평균 시간입니다.
- 의미: 장애 대응 속도를 나타냅니다.
- 데이터 출처: `data/incidents.json`의 `started_at`과 `resolved_at` 값을 사용합니다.
- 계산 방식: 장애별 복구 시간 평균을 계산합니다.

### 4) Change Failure Rate
- 정의: 전체 배포 중 실패하거나 롤백이 발생한 비율입니다.
- 의미: 배포 품질과 안정성을 보여줍니다.
- 데이터 출처: `data/deployments.json`의 `status` 필드입니다.
- 계산 방식: `success` 대비 `failed`, `partial`, `rollback` 비율입니다.

## 데이터 출처와 기록 방법

### 배포 기록
`data/deployments.json`에 배포 정보를 기록합니다.

예시:

```json
[
  {
    "id": "deploy-001",
    "status": "success",
    "started_at": "2026-09-01T09:00:00Z",
    "deployed_at": "2026-09-01T10:30:00Z"
  }
]
```

필드 설명:
- `id`: 배포 식별자
- `status`: `success`, `failed`, `partial`, `rollback`
- `started_at`: 변경 작업 시작 시각
- `deployed_at`: 실제 배포 완료 시각

이 값은 GitHub Actions 실행 시 읽어서 평균 리드 타임, 배포 빈도, 실패율을 계산합니다.

### 장애 기록
`data/incidents.json`에 장애 정보를 기록합니다.

예시:

```json
[
  {
    "id": "incident-001",
    "status": "resolved",
    "started_at": "2026-09-03T00:00:00Z",
    "resolved_at": "2026-09-03T04:00:00Z"
  }
]
```

필드 설명:
- `id`: 장애 ID
- `status`: `open`, `resolved`, `monitoring`
- `started_at`: 장애 시작 시각
- `resolved_at`: 장애 복구 완료 시각

### 실 운영에서의 추천 기록 방식
- GitHub Releases 또는 Deployments API를 활용해 배포 기록을 자동화
- GitHub Issues 또는 프로젝트 보드를 이용해 장애 이슈 등록
- 외부 모니터링 도구가 있으면 해당 데이터를 export해 JSON으로 변환
- 이 저장소는 실 배포·장애 API 연결이 아직 없으므로 현재는 JSON 파일 기반으로 동작합니다.

## 저장소 구조

```text
.
├── .github/
│   └── workflows/
│       └── metrics.yml
├── data/
│   ├── deployments.json
│   └── incidents.json
├── README.md
├── metrics.py
├── metrics.json
├── weekly-report.md
├── dashboard.html
├── tests/
│   └── test_metrics.py
└── .gitignore
```

## 로컬 실행 방법

```bash
python metrics.py
python -m unittest discover -s tests -v
```

실행 후 다음 파일이 생성됩니다.
- `metrics.json`: 계산 결과 JSON
- `weekly-report.md`: 주간 DORA 보고서

## GitHub Actions 실행 방법

1. GitHub 저장소에서 Actions 탭을 엽니다.
2. `DORA Metrics Collection` 워크플로우를 선택합니다.
3. `Run workflow`를 클릭해 수동 실행합니다.
4. 작업이 끝나면 `Artifacts`에서 `dora-metrics`를 다운로드합니다.

또는 매주 월요일 오전 9시 UTC에 자동 실행되도록 설정되어 있습니다.

## null 처리 규칙

실제 데이터가 없거나 계산할 수 없으면 값은 `null`로 표시하고, `reason` 필드에 사유를 적습니다.

예시:

```json
{
  "lead_time": {
    "metric": "lead_time",
    "value": null,
    "unit": "hours",
    "reason": "No valid deployment start/end timestamps found for lead time calculation."
  }
}
```

중요한 점:
- GitHub Actions 성공/실패만으로 실제 배포·장애를 간주하지 않습니다.
- `success` 또는 `failure`는 배포 기록의 상태일 뿐이며, 운영 장애를 의미하지 않습니다.
- 실제 운영 데이터가 없을 경우에는 값을 `null`로 남겨야 합니다.

## 대시보드 설명

`dashboard.html`은 계산된 결과를 간단하게 보여주는 정적 대시보드입니다.

- `metrics.json`을 불러와 4개 지표를 표시
- 값이 없으면 `null` 표시
- `reason` 메시지를 함께 표시

브라우저로 열어 확인할 수 있습니다.

## 현재 구현 상태와 남은 과제

### 구현 완료된 내용
- GitHub Actions 워크플로우 구성
- DORA 4대 지표 계산 로직
- JSON 아티팩트 생성
- 주간 보고서 자동 생성
- 정적 대시보드 구현
- 빈 데이터일 때 `null`과 사유 표시

### 아직 구현되지 않은 부분
- 실제 배포 API 연동
- 실제 장애 이슈/모니터링 로그 연동
- 프로덕션/스테이징 환경 구분
- 자동으로 GitHub Releases 또는 Deployments에서 데이터 수집
- 대시보드 외부 배포(예: GitHub Pages)

### 추가 작업이 필요한 이유
이 저장소는 현재 예제 구조이며, 실제 DORA 지표는 배포와 장애를 정확히 기록하는 데이터 집계가 필요합니다. 그러므로 다음 단계가 필요합니다.

1. 배포 기록을 자동으로 넣는 파이프라인 구성
2. 운영 장애를 기록하는 규칙 정립
3. GitHub Actions에서 실제 배포 이벤트 수집 로직 추가
4. 팀별 기준 정의(배포 기준, 장애 정의, 복구 기준)

## 참고

이 프로젝트는 DORA 지표를 실습하고, GitHub Actions에서 자동수집·아티팩트 저장까지 확인하기 위한 예제입니다. 실제 사용 전에는 운영 데이터 수집 규칙을 팀에 맞춰 정리해야 합니다.
