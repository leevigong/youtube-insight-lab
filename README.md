# youtube-insight-lab

유튜브 알고리즘을 카테고리별로 파헤치는 분석 서비스

> **이 프로젝트는 100% 바이브 코딩으로 만들어집니다.**
> Claude Code와 함께 대화하면서 코드를 작성하고, 설계하고, 발전시켜 나갑니다.
> 여러 Claude Code Plugin을 시도하며 프로젝트를 진행합니다.

## 목표

- 유튜브 영상 카테고리별 알고리즘 패턴 분석
- 조회수, 좋아요, 제목, 업로드 시간대 등 다양한 지표 분석
- 미디어팀의 채널 운영 전략에 활용할 수 있는 실무 도구

## 왜 Python?

- **YouTube Data API 공식 클라이언트가 가장 잘 지원됨**
- 데이터 분석 생태계(pandas)가 압도적
- FastAPI로 가볍고 빠른 API 서버 구축 가능
- 바이브 코딩과 궁합이 좋음

## 기술 스택

- **Backend**: Python + FastAPI
- **YouTube API**: google-api-python-client
- **데이터 분석**: pandas

## 개발 단계

1. 기반 세팅 (FastAPI + YouTube API 연동)
2. 카테고리별 인기 영상 분석
3. 영상 상세 분석 (제목, 썸네일, 조회수 패턴, 업로드 시간대)
4. 트렌드 추적
5. 서비스 확장 (DB, 프론트엔드)

## 벤치마크

| 서비스 | 특징 | 참고 포인트 |
|---|---|---|
| **vidIQ** | SEO 점수, CTR/리텐션 추적 | 알고리즘 핵심 지표 대시보드 |
| **TubeLab** | 니치 포화도, 아웃라이어 영상 탐지 | 카테고리별 정량 분석 (가장 유사) |
| **Social Blade** | 채널 성장 추이, 랭킹 | 시계열 트렌드 시각화 |

**차별점**: 기존 서비스는 채널/영상 단위 분석에 집중. yt-insight-lab은 **카테고리 간 알고리즘 패턴 비교**에 초점.

## 시작하기

### 1. YouTube API Key 발급

1. [YouTube Data API v3](https://console.cloud.google.com/marketplace/product/google/youtube.googleapis.com) 페이지에서 API 사용 설정
2. **APIs & Services > Credentials > Create Credentials > API Key**로 키 발급

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 발급받은 API Key 입력:

```
YOUTUBE_API_KEY=발급받은키
```

### 3. 설치 및 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### 4. 테스트

```bash
pytest
```
