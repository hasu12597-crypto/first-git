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
- 정의: 배포된 커밋의 실제 커밋 시점부터 GitHub Pages 운영 배포 성공 시점까지의 시간입니다.
- 의미: 변경이 얼마나 빠르게 고객에게 전달되는지를 보여줍니다.
- 데이터 출처: GitHub Deployments의 커밋 SHA, 해당 커밋 API의 커밋 시각, 배포 status API의 성공 시각입니다.
- 계산 방식: 성공 배포의 유효한 pair 평균입니다. 1분 미만은 보고서와 대시보드에서 초 단위로 표시합니다.

### 2) Deployment Frequency
- 정의: 일정 기간(기본 7일) 동안 몇 번 배포가 발생했는지를 나타냅니다.
- 의미: 팀의 배포 속도와 릴리즈 주기를 보여줍니다.
- 데이터 출처: GitHub Pages deployment status API의 성공 시각(`deployed_at`)을 기준으로 집계합니다.
- 계산 방식: 최근 7일 안의 `success` 운영 배포만 세며, 실패 배포는 빈도에서 제외합니다.

### 3) MTTR (Mean Time To Recovery)
- 정의: 장애 발생 시점부터 복구 완료 시점까지의 평균 시간입니다.
- 의미: 장애 대응 속도를 나타냅니다.
- 데이터 출처: `data/incidents.json`의 `started_at`과 `resolved_at` 값을 사용합니다.
- 계산 방식: 장애별 복구 시간 평균을 계산합니다.

### 4) Change Failure Rate
- 정의: 운영에 반영된 성공 배포 중 장애, 롤백, 핫픽스 등 조치가 필요했던 배포의 비율입니다.
- 의미: 배포 품질과 안정성을 보여줍니다.
- 데이터 출처: `incident` 라벨 GitHub Issue와 배포 기록의 `id` 또는 `commit_sha` 연결입니다.
- 계산 방식: 성공 운영 배포 중 incident Issue에 배포 ID/SHA가 연결된 고유 배포 수의 비율입니다. 연결 정보가 없거나 일부 장애가 연결되지 않으면 완전성을 보장할 수 없어 `null`입니다.

### Deployment Job Failure Rate
- 정의: 전체 완료된 배포 작업 중 `failure`, `error`, `rollback`, `cancelled` 등으로 끝난 작업의 비율입니다.
- 이 값은 DORA Change Failure Rate와 별개이며, `deployment_failure_rate_value`로 저장합니다.

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
- `status`: `success`, `failed`, `failure`, `partial`, `rollback`, `error`, `cancelled`
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
- GitHub Pages 배포 워크플로우가 배포 시각과 커밋 SHA를 `data/deployments.json`에 기록합니다.
- GitHub Issues를 이용해 장애를 기록하고, 반드시 `incident` 라벨을 붙여 MTTR 계산에 사용합니다. 일반 `bug` 이슈는 자동 장애로 집계하지 않습니다.
- GitHub Actions에서 `GITHUB_TOKEN`을 사용해 Issues를 조회하고, `started_at`과 `resolved_at`을 비교해 복구 시간을 계산합니다.
- 실제 데이터가 없으면 `null`과 `reason`을 유지하며, 값은 임의로 만들어 넣지 않습니다.

### GitHub Pages 실제 배포 연동 규칙
- 배포 기록은 코드 변경이 있거나 GitHub Pages 배포 workflow가 실행될 때 생성됩니다.
- `commit_timestamp`는 커밋 시각을 기준으로 사용하고, `deployed_at`은 실제 배포 완료 시각을 기록합니다.
- Lead Time은 작업 시작 시점이 아니라 코드 커밋 시점부터 운영 배포 성공까지의 시간으로 계산합니다.

### 장애 기록 규칙
- 자동 집계 조건은 **AND 조건**입니다: GitHub Issue이면서 `incident` 라벨을 가져야 합니다. Pull Request는 제외됩니다.
- `bug` 또는 `production` 라벨만 있는 이슈는 집계하지 않습니다. 이 라벨을 함께 붙일 수는 있지만 `incident` 라벨을 대신할 수 없습니다.
- `started_at`은 이슈 생성 시각, `resolved_at`는 종료 시각입니다.
- 장애 이슈 본문에 다음처럼 관련 배포의 ID와 커밋 SHA를 기록합니다. 두 값은 `data/deployments.json`의 `id`와 `commit_sha`에 연결할 때 사용합니다.

```text
Deployment ID: pages-123456789
Deployment SHA: abc123...
```

- 배포 ID를 모르면 `Deployment SHA`만 기록해도 됩니다. 해당 SHA가 배포 기록의 `commit_sha`와 일치하는지 확인합니다.
- 같은 배포를 여러 incident Issue가 참조해도 deployment ID/SHA 기준으로 한 번만 CFR에 포함합니다.
- `incident` Issue가 없거나, Issue는 있지만 배포 ID/SHA가 없거나 일치하지 않으면 CFR은 `null`이며 사유에 완전성 판단 불가를 표시합니다.

### GitHub Actions 권한
- `metrics.yml`: `contents: read`, `issues: read`만 사용합니다. 저장소 쓰기 권한, Pull Request 생성·승인 권한은 부여하지 않습니다.
- GitHub Deployments API 조회에는 `deployments: read`가 필요하므로 두 workflow에 해당 권한을 추가합니다. 쓰기 권한은 사용하지 않습니다.
- `pages-deploy.yml`: Pages 게시에 필요한 `pages: write`, OIDC 인증에 필요한 `id-token: write`, 소스와 배포·장애 기록 조회에 필요한 `contents: read`, `deployments: read`, `issues: read`만 사용합니다.
- 두 workflow 모두 job 단위로 권한을 선언하며, `pull-requests` 권한과 전체 저장소 `write` 권한은 선언하지 않습니다.

### API 권한 오류 표시
- Deployments API 또는 Issues API가 `401`, `403` 등으로 실패하면 이를 데이터 없음으로 숨기지 않습니다.
- 요청은 `GITHUB_API_URL`을 기준으로 `https://api.github.com/repos/소유자/저장소/deployments` 및 `.../issues` 형태로 구성됩니다. Actions에서는 `github.api_url`, 저장소 이름은 `github.repository`를 사용합니다.
- `metrics.json`의 `collection_errors`에 소스, 실제 요청 URL, 오류 유형, HTTP 상태, API 응답 메시지가 기록됩니다.
- `weekly-report.md`에는 `Collection Errors` 항목으로 표시되고, 대시보드 상태도 `API 데이터 수집 오류`로 표시됩니다.
- 수집 오류가 있으면 `metrics.py`가 산출물을 먼저 작성한 뒤 종료 코드 `1`을 반환합니다. 따라서 `if: always()` 아티팩트 업로드는 실행되지만 최종 workflow 결과는 실패입니다.

### 계산 근거 확인
- `metrics.json`의 `deployment_evidence`에 전체 건수, 고유 건수, 중복 ID, 상태별 건수, 배포별 커밋 시각·성공 시각·Lead Time 초가 기록됩니다.
- 현재 대상 저장소의 실제 공개 API 결과는 배포 4건, 고유 ID 4건, 중복 0건, `success` 2건과 `failure` 2건입니다. 따라서 성공한 운영 배포 빈도는 2.0/week, 배포 작업 실패율은 2/4 = 0.5입니다. incident 연결이 없으므로 DORA Change Failure Rate는 `null`입니다.
- `incident` 라벨 Issue가 없으면 장애 데이터는 0건이며, MTTR은 `null`로 남습니다. 장애 데이터를 만들거나 예시 데이터를 섞지 않습니다.

### 404 발생 시 GitHub 확인 절차
1. 실패한 Actions 실행의 `dora-metrics` 아티팩트를 다운로드합니다.
2. `metrics.json`의 `collection_errors`에서 `url`, `status`, `message`를 확인합니다. 토큰 값은 로그나 아티팩트에 기록하지 않습니다.
3. URL이 다음 대상과 일치하는지 확인합니다: `https://api.github.com/repos/hasu12597-crypto/first-git/deployments`, `https://api.github.com/repos/hasu12597-crypto/first-git/issues?state=all&labels=incident&per_page=100`.
4. URL이 맞고 `404 Not Found`이면 저장소가 실제로 해당 owner/name으로 존재하는지, Actions 실행의 `GITHUB_REPOSITORY`가 `hasu12597-crypto/first-git`인지, `GITHUB_TOKEN`이 이 저장소에 접근할 수 있는지 확인합니다. 비공개 저장소는 권한 부족도 404로 응답할 수 있습니다.
5. `401` 또는 `403`이면 토큰 만료/무효 또는 workflow의 `deployments: read`·`issues: read` 권한을 확인합니다. 권한 오류는 데이터 없음으로 처리되지 않고 workflow를 실패시킵니다.

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

### 권한 점검
워크플로우 파일의 `permissions`는 다음 최소 범위만 허용합니다.

```yaml
permissions:
  contents: read
  deployments: read
  issues: read
```

Pages 배포 workflow에는 여기에 `pages: write`와 `id-token: write`가 추가됩니다. GitHub 저장소 Settings의 Actions 권한을 `Read repository contents permission`으로 두어도 이 workflow의 명시적 job 권한이 필요한 범위만 요청합니다.

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
- 프로덕션/스테이징 환경 구분
- 외부 모니터링 도구의 장애 타임스탬프 연동

### 추가 작업이 필요한 이유
이 저장소는 현재 예제 구조이며, 실제 DORA 지표는 배포와 장애를 정확히 기록하는 데이터 집계가 필요합니다. 그러므로 다음 단계가 필요합니다.

1. 배포 기록을 자동으로 넣는 파이프라인 구성
2. 운영 장애를 기록하는 규칙 정립
3. GitHub Actions에서 실제 배포 이벤트 수집 로직 추가
4. 팀별 기준 정의(배포 기준, 장애 정의, 복구 기준)

## 참고

이 프로젝트는 DORA 지표를 실습하고, GitHub Actions에서 자동수집·아티팩트 저장까지 확인하기 위한 예제입니다. 실제 사용 전에는 운영 데이터 수집 규칙을 팀에 맞춰 정리해야 합니다.
