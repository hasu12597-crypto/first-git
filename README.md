# DORA 메트릭 수집 자동화

OSS 기반 SW 프로그래밍 과제입니다. GitHub Actions와 GitHub API로 DORA 4개 지표를 수집하고, 대시보드·JSON 결과·주간 보고서를 자동 생성합니다.

## 대시보드

![DORA 4개 지표 대시보드 실행 결과](docs/%EC%8A%A4%ED%81%AC%EB%A6%B0%EC%83%B7%202026-09-15%20155357.png)

2026년 9월 15일 실행 결과: **Lead Time 32초 · 배포 빈도 주당 5회 · MTTR 데이터 없음 · 변경 실패율 28.57%**.
캡처는 해당 실행 시점의 결과이며, 최신 수치는 Actions 아티팩트에서 확인할 수 있습니다.

## 지표와 계산 기준

| 지표 | 계산 방법 | 데이터 출처 |
| --- | --- | --- |
| Lead Time | 배포된 커밋 시각부터 배포 성공까지 걸린 시간의 평균 | Commits · Deployments · Deployment Statuses API |
| Deployment Frequency | 최근 7일간 성공한 운영 배포 수 | Deployments · Deployment Statuses API |
| MTTR | 유효한 장애 발생·복구 시각 차이의 평균 | `incident` 라벨의 GitHub Issues |
| Change Failure Rate | 최근 7일간 실패한 배포 수 ÷ 완료된 배포 수 × 100 | Deployments · Deployment Statuses API |

배포 집계 대상은 `github-pages` 환경입니다. 변경 실패율은 수업 기준을 적용하며, 현재 코드의 상태 분류는 다음과 같습니다.

- 성공: `success`
- 실패: `failure`, `failed`, `error`, `cancelled`, `partial`, `rollback`
- 제외: `queued`, `waiting`, `in_progress`, `pending`, `unknown` 등 완료 여부를 판정할 수 없는 상태

실패율의 집계 시각은 배포 상태 시각을 우선 사용하고, 없으면 배포 완료·생성 시각을 사용합니다. 단순 CI 작업 실패는 집계하지 않으며, 이 비율을 운영 장애 발생률과 동일하게 해석하지 않습니다.

## 실행 및 결과 확인

1. 저장소의 **Settings → Pages → Source**를 **GitHub Actions**로 설정합니다.
2. Pages 배포 성공 후 [Actions](https://github.com/hasu12597-crypto/first-git/actions)에서 **DORA Metrics Collection → Run workflow**를 실행합니다.
3. 완료된 실행의 **Artifacts → dora-metrics**를 다운로드하고 압축을 풉니다.
4. `dashboard.html`을 브라우저로 열어 결과를 확인합니다. 데이터가 HTML에 포함되어 별도 서버 없이 열 수 있습니다.

수집 워크플로는 **매주 월요일 09:00 UTC(한국 시간 18:00)**와 **`main` 푸시 시** 실행되며, 수동 실행도 지원합니다.

| 아티팩트 파일 | 내용 |
| --- | --- |
| `metrics.json` | 지표 값, 계산 근거, 수집 오류 |
| `weekly-report.md` | 주간 지표 요약 보고서 |
| `dashboard.html` | DORA 4개 지표 대시보드 |

## 데이터 기록과 한계

- 장애는 GitHub Issue에 `incident` 라벨을 붙여 기록합니다. Pull Request와 일반 `bug` 이슈는 제외합니다.
- 이슈 생성·종료 시각을 장애 발생·복구 시각으로 사용하므로 실제 시각과 차이가 날 수 있습니다. 관련 배포 ID/SHA를 본문에 남기면 추적에 도움이 됩니다.
- 유효한 데이터가 없으면 `null`과 사유를 표시합니다. 현재 MTTR은 장애·복구 기록이 없어 실데이터 계산을 확인하지 못했습니다.
- API 오류는 `collection_errors`와 보고서·대시보드에 표시하며, 아티팩트를 남긴 뒤 워크플로를 실패로 처리합니다.
- 아티팩트는 실행 시점의 결과입니다. 새 데이터를 보려면 최신 실행 결과를 다운로드합니다.

## 주요 파일

| 파일 | 역할 |
| --- | --- |
| `.github/workflows/metrics.yml` | 정기·수동 수집 및 아티팩트 업로드 |
| `.github/workflows/pages-deploy.yml` | GitHub Pages 배포 |
| `metrics.py` | API 조회, 지표 계산, 보고서·대시보드 생성 |
| `tests/test_metrics.py` | 계산 및 오류 처리 테스트 |
| `data/` | 로컬 배포·장애 기록 |
| `docs/` | 제출용 대시보드 캡처 |

수집에는 `GITHUB_TOKEN`과 `contents: read`, `deployments: read`, `issues: read` 권한을 사용합니다. Pages 배포에는 `pages: write`, `id-token: write` 권한도 사용합니다.

로컬 실행 및 테스트:

```bash
python metrics.py
python -m unittest discover -s tests -v
```

로컬 API 수집에는 `GITHUB_REPOSITORY`와 적절한 권한의 `GITHUB_TOKEN` 설정이 필요합니다. 로컬 데이터 파일은 비워 두거나 실제 기록만 사용합니다.
