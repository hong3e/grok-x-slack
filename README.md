# Grok X Stock Market Notifier 📈📧

이 프로젝트는 **xAI Grok API**의 실시간 X(구 트위터) 검색 기능(`x_search`)을 활용하여, 최근 24시간 동안 X에서 가장 인기 있는(좋아요, 조회수, RT가 높은) 주식 투자 관련 게시글을 수집 및 요약한 뒤 **이메일**로 전송해 주는 자동화 스크립트입니다.

---

## 🛠 주요 기능
- **실시간 X 트렌드 검색**: xAI Grok API의 서버사이드 X 검색(`x_search` tool)을 통해 최신 주식 관련 트윗을 실시간 검색 및 집계합니다.
- **AI 요약 & 가독성 향상**: Grok 모델이 단순히 링크만 주는 것이 아니라, 핵심 분석 내용과 주요 수치(조회수, 좋아요 등)를 가독성 높은 형태의 HTML 메일 포맷으로 변환하여 요약합니다.
- **이메일 연동**: Gmail SMTP를 사용하여 지정된 이메일 주소로 리포트를 자동 발송합니다.

---

## 📁 폴더 및 파일 구조
```text
grok-x-slack/
├── .env                # API 키 및 설정 (로컬 환경 실행용, .gitignore에 등록됨)
├── .env.template       # 환경 변수 템플릿 파일
├── .gitignore          # Git 제외 파일 설정
├── requirements.txt    # 의존성 패키지 목록
├── main.py             # 주 실행 파이썬 스크립트
└── README.md           # 설명 문서
```

---

## 🚀 시작하기

### 1. 요구사항 및 라이브러리 설치
이 프로젝트는 **Python 3.8 이상**이 필요합니다.

```bash
# 가상환경 생성 (선택사항)
python -m venv venv
# 가상환경 활성화 (Windows)
.\venv\Scripts\activate
# 가상환경 활성화 (Mac/Linux)
source venv/bin/activate

# 의존 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`grok-x-slack` 폴더 아래의 `.env` 파일을 열고 다음과 같이 본인의 API 키 정보를 입력합니다:

```env
# xAI Grok API 키 입력 (https://console.x.ai/ 에서 발급 가능)
XAI_API_KEY=xai-your-api-key-here

# Grok 모델명 (x.ai의 Responses API를 지원하는 최신 모델 설정, 예: grok-2)
XAI_MODEL=grok-2

# 이메일 발송 설정 (Gmail SMTP 사용)
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password-here
RECEIVER_EMAIL=recipient@example.com

# X에서 탐색할 주식 검색 프롬프트 (필요에 따라 수정 가능)
SEARCH_PROMPT=Find the most popular posts about stock investing, KOSPI, KOSDAQ, NASDAQ, NVIDIA, Tesla, and finance from the last 24 hours on X. Focus on posts with high likes, views, or retweets.
```

### 3. 스크립트 실행
로컬에서 수동으로 스크립트를 테스트하려면 다음과 같이 실행합니다:

```bash
python main.py
```

---

## ⏰ 매일 자동 실행(스케줄링) 설정 방법

### 방법 A: Linux / macOS (Crontab 사용)
매일 오전 9시에 스크립트를 실행하려면 `crontab`에 등록합니다:

1. 터미널에서 크론탭 편집 실행:
   ```bash
   crontab -e
   ```
2. 아래 줄을 추가합니다 (실제 파이썬 경로 및 프로젝트 경로로 수정):
   ```cron
   0 9 * * * cd /path/to/hong3e/grok-x-slack && /path/to/hong3e/grok-x-slack/venv/bin/python main.py >> /path/to/hong3e/grok-x-slack/cron.log 2>&1
   ```

---

### 방법 B: Windows (작업 스케줄러 사용)
Windows 환경에서 매일 자동 실행하도록 설정하는 방법입니다:

1. **작업 스케줄러(Task Scheduler)** 열기 (`Win + R` 누른 후 `taskschd.msc` 입력).
2. 우측 메뉴에서 **작업 만들기(Create Task)** 선택.
3. **일반(General)** 탭:
   - 이름: `Grok X Stock Notifier` 입력.
   - "사용자가 로그온할 때만 실행" 또는 "로그온 여부와 관계없이 실행" 선택.
4. **트리거(Triggers)** 탭:
   - [새로 만들기...] 클릭 -> 작업 시작: **예약 상태**, **매일(Daily)** 로 설정하고 원하는 시간(예: 오전 09:00) 지정.
5. **동작(Actions)** 탭:
   - [새로 만들기...] 클릭 -> 동작: **프로그램 시작**.
   - 프로그램/스크립트: `python` (또는 가상환경의 python.exe 절대 경로, 예: `D:\Documents\GitHub\hong3e\grok-x-slack\venv\Scripts\python.exe`).
   - 인수 추가(선택 사항): `main.py`
   - 시작 위치(선택 사항): 스크립트가 있는 폴더 경로 (예: `D:\Documents\GitHub\hong3e\grok-x-slack`).
6. 저장 후 완료.

---

### 방법 C: GitHub Actions 사용 (추천 - 별도 서버 불필요)
GitHub 저장소에 올려두면 매일 깃허브 서버에서 자동으로 실행되고 이메일로 전달되는 매우 편리한 방식입니다.

1. `.github/workflows/grok_email_notifier.yml` 파일을 아래와 같이 생성합니다:
   ```yaml
   name: Daily Grok X Stock Notifier

   on:
     schedule:
       # 매일 한국시간 오전 9시 (UTC 00:00) 실행
       - cron: '0 0 * * *'
     workflow_dispatch: # 수동 실행 버튼 활성화

   jobs:
     notify:
       runs-on: ubuntu-latest
       steps:
         - name: Checkout code
           uses: actions/checkout@v4

         - name: Set up Python
           uses: actions/setup-python@v5
           with:
             python-version: '3.10'

         - name: Install dependencies
           run: |
             cd grok-x-slack
             python -m pip install --upgrade pip
             pip install -r requirements.txt

         - name: Run script
           env:
             XAI_API_KEY: ${{ secrets.XAI_API_KEY }}
             GMAIL_USER: ${{ secrets.GMAIL_USER }}
             GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
             RECEIVER_EMAIL: ${{ secrets.RECEIVER_EMAIL }}
             XAI_MODEL: grok-2
             NON_INTERACTIVE: true
           run: |
             cd grok-x-slack
             python main.py
   ```
2. GitHub 저장소의 **Settings > Secrets and variables > Actions** 메뉴로 이동합니다.
3. **Repository secrets**에 `XAI_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `RECEIVER_EMAIL`을 등록합니다.
