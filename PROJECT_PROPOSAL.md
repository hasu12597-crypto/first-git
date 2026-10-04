# DevFlow: 개발팀 협업·배포 품질 관리 플랫폼

## 1. 프로젝트 개요

DevFlow는 GitHub Issues, Projects, Pull Requests, Actions 데이터를 하나의 화면에서 확인하고 관리하는 개발팀 협업·배포 품질 관리 플랫폼이다. 기존에 구축한 DORA Metrics 대시보드를 확장하여 작업 흐름과 배포 품질을 함께 관리하는 것을 목표로 한다.

## 2. 문제 정의

개발팀은 작업이 어느 단계에 있는지, 코드 리뷰가 얼마나 지연되는지, 배포가 안정적인지 여러 GitHub 화면을 오가며 확인해야 한다. 이 때문에 작업 지연과 배포 문제를 빠르게 파악하기 어렵다.

DevFlow는 칸반 보드와 자동화된 지표를 제공하여 작업 흐름, 협업 상태, 배포 품질을 한눈에 확인할 수 있도록 한다.

## 3. 핵심 기능

### 3.1 칸반 기반 작업 관리

- Backlog, To Do, In Progress, Review, Done 상태 관리
- Bug 및 Feature 이슈 템플릿 제공
- 라벨과 마일스톤을 이용한 스프린트 관리
- Cycle Time, Velocity, Burndown 분석

### 3.2 DORA 및 Flow Metrics 대시보드

- Lead Time
- Deployment Frequency
- MTTR
- Change Failure Rate
- 이슈 Cycle Time 및 Pull Request 리뷰 시간

### 3.3 자동화된 CI/CD와 품질 관리

- GitHub Actions를 이용한 자동 테스트와 배포
- Pull Request 파일 경로 기반 자동 라벨 부여
- Feature Flag를 이용한 안전한 기능 공개
- 테스트 실패 및 배포 실패 상태 확인

## 4. 기술 스택

- Frontend: HTML, CSS, JavaScript
- Backend 및 데이터 수집: Python
- Database: SQLite 또는 PostgreSQL
- 협업 관리: GitHub Issues, Projects v2, Discussions
- CI/CD: GitHub Actions
- API: GitHub REST API
- 배포: GitHub Pages

## 5. 16주 마일스톤

| 기간 | 목표 |
|---|---|
| 1~2주 | 프로젝트 설계, GitHub 저장소, Project, 이슈 템플릿 구성 |
| 3~4주 | 칸반 보드와 라벨·마일스톤 기반 협업 규칙 구축 |
| 5~6주 | GitHub Flow와 Pull Request 코드 리뷰 규칙 적용 |
| 7~8주 | GitHub Actions 기반 CI/CD 구축 |
| 9~10주 | DORA Metrics 수집 및 대시보드 구현 |
| 11~12주 | Flow Metrics와 Pull Request 분석 추가 |
| 13~14주 | Feature Flag 및 배포 자동화 적용 |
| 15주 | 테스트, 보안 점검, 성능 개선 |
| 16주 | 문서화, 발표 자료 작성, 최종 배포 |

## 6. 기대 효과

- 작업 지연과 병목 구간을 빠르게 파악할 수 있다.
- 코드 리뷰와 배포 과정을 표준화할 수 있다.
- DORA 및 Flow Metrics를 기반으로 개발 프로세스를 개선할 수 있다.
- GitHub 협업 기능과 CI/CD 자동화를 실제 프로젝트에 적용할 수 있다.

## 7. AI 활용 공개

- 사용 도구: ChatGPT/Codex
- 사용 시기: 프로젝트 주제 선정 및 제안서 초안 작성 단계
- 활용 범위: 프로젝트 아이디어 구체화, 핵심 기능과 기술 스택 정리, 16주 마일스톤 초안 작성, 문서 표현 검토
- 입력 프롬프트 요약: GitHub Projects, DORA Metrics, GitHub Actions를 활용하는 학기 프로젝트의 주제와 기능, 기술 스택, 기간별 계획을 제안하도록 요청함
- 검증 방법: 제안서의 기술 내용과 GitHub 기능 지원 여부를 직접 확인하고, 실제 저장소의 workflow와 프로젝트 설정에 적용 가능한지 검토함

AI가 생성한 초안은 그대로 제출하지 않고 프로젝트 상황에 맞게 수정했으며, 사실과 기술 정보는 제출 전에 직접 확인했다.
