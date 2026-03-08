# 📊 매출 대시보드

구글 시트 데이터를 실시간으로 읽어 권한 있는 사용자에게만 보여주는 Streamlit 대시보드입니다.

## ✨ 기능

- 🔐 Google OAuth 로그인 (허용된 계정만 접근)
- 📊 월별 매출 vs 지출 막대그래프
- 📈 월별 순이익 추이 라인 차트
- 🥧 지출 항목별 원형 그래프
- 💰 매출 / 지출 상위 항목 가로 막대
- 📋 KPI 카드 (총매출, 총지출, 순이익, 거래건수)
- 📋 상세 거래 내역 테이블
- 🔄 수동 데이터 새로고침

---

## 🚀 로컬 실행

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. secrets.toml 설정
`.streamlit/secrets.toml` 파일에서 아래 항목을 실제 값으로 교체하세요:

```toml
[oauth]
client_id     = "YOUR_OAUTH_CLIENT_ID"      ← Google Cloud Console에서 복사
client_secret = "YOUR_OAUTH_CLIENT_SECRET"  ← Google Cloud Console에서 복사
redirect_uri  = "http://localhost:8501"

[auth]
allowed_emails = ["허용할이메일@gmail.com"]
```

### 3. 앱 실행
```bash
python3 -m streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## ☁️ Streamlit Cloud 배포 방법

### 1단계: GitHub에 코드 올리기
```bash
git init
git add app.py requirements.txt
# ⚠️ secrets.toml은 절대 올리지 않음! (.gitignore에 추가)
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2단계: .gitignore 생성 (보안 중요!)
```
.streamlit/secrets.toml
inner-legacy-429605-t1-52ed6365ff4f.json
__pycache__/
*.pyc
```

### 3단계: Streamlit Cloud에서 앱 배포
1. [share.streamlit.io](https://share.streamlit.io) 접속
2. `New app` → GitHub 저장소 선택
3. Main file: `app.py`
4. `Advanced settings` → **Secrets** 탭에 아래 내용 전체 붙여넣기

```toml
[oauth]
client_id     = "실제 클라이언트 ID"
client_secret = "실제 클라이언트 보안 비밀"
redirect_uri  = "https://YOUR-APP-NAME.streamlit.app"

[auth]
allowed_emails = ["허용할이메일@gmail.com"]

[service_account]
type                        = "service_account"
project_id                  = "inner-legacy-429605-t1"
private_key_id              = "52ed6365ff4f..."
private_key                 = "-----BEGIN PRIVATE KEY-----\n..."
client_email                = "sheets-reader@inner-legacy-429605-t1.iam.gserviceaccount.com"
client_id                   = "103774165397848403485"
auth_uri                    = "https://accounts.google.com/o/oauth2/auth"
token_uri                   = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url        = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

5. `Deploy!` 클릭

### 4단계: Google Cloud Console에서 리디렉션 URI 추가
1. [console.cloud.google.com](https://console.cloud.google.com) → `클라이언트` 메뉴
2. 생성한 OAuth 클라이언트 클릭
3. **승인된 리디렉션 URI**에 추가:
   ```
   https://YOUR-APP-NAME.streamlit.app
   ```
4. secrets.toml의 `redirect_uri`도 같은 주소로 변경

---

## 📁 파일 구조

```
project/
├── app.py                              # 메인 Streamlit 앱
├── test_connection.py                  # 구글 시트 연동 테스트
├── requirements.txt                    # 패키지 목록
├── README.md                           # 이 파일
└── .streamlit/
    └── secrets.toml                    # 🔒 비밀키 (Git에 올리지 말 것!)
```

---

## ⚙️ secrets.toml 전체 예시

```toml
[oauth]
client_id     = "123456789-abcdef.apps.googleusercontent.com"
client_secret = "GOCSPX-xxxxxxxxxxxxxxxx"
redirect_uri  = "http://localhost:8501"   # 로컬 / 배포 후 실제 URL로 변경

[auth]
allowed_emails = [
  "admin@gmail.com",
  "partner@company.com",
]

[service_account]
type                        = "service_account"
project_id                  = "your-project-id"
private_key_id              = "key-id"
private_key                 = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email                = "service@your-project.iam.gserviceaccount.com"
client_id                   = "000000000000000000000"
auth_uri                    = "https://accounts.google.com/o/oauth2/auth"
token_uri                   = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url        = "https://www.googleapis.com/robot/v1/metadata/x509/..."