import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import os

st.set_page_config(page_title="구글 시트 연동 테스트", page_icon="📊")

st.title("📊 구글 시트 연동 테스트")

# ── 설정 ──────────────────────────────────────────────
SPREADSHEET_ID = "1D_s4eh_S1YKHq-jppkNSflfuIa-Eh50MbTOg5caZgF8"
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "inner-legacy-429605-t1-52ed6365ff4f.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# ── 연결 함수 ──────────────────────────────────────────
@st.cache_data(ttl=300)  # 5분 캐시
def load_data(sheet_name: str = None):
    """구글 시트에서 데이터를 읽어옵니다."""
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)

        # 시트 이름이 없으면 첫 번째 시트 사용
        if sheet_name:
            worksheet = spreadsheet.worksheet(sheet_name)
        else:
            worksheet = spreadsheet.get_worksheet(0)

        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df, worksheet.title, None
    except FileNotFoundError:
        return None, None, f"❌ 서비스 계정 파일을 찾을 수 없습니다: {SERVICE_ACCOUNT_FILE}"
    except gspread.exceptions.SpreadsheetNotFound:
        return None, None, "❌ 스프레드시트를 찾을 수 없습니다. 서비스 계정 이메일로 시트를 공유했는지 확인하세요."
    except gspread.exceptions.APIError as e:
        return None, None, f"❌ API 오류: {str(e)}"
    except Exception as e:
        return None, None, f"❌ 오류 발생: {str(e)}"


# ── UI ────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"**스프레드시트 ID:** `{SPREADSHEET_ID}`")
st.markdown(f"**서비스 계정:** `sheets-reader@inner-legacy-429605-t1.iam.gserviceaccount.com`")
st.markdown("---")

if st.button("🔄 데이터 불러오기", type="primary", use_container_width=True):
    st.cache_data.clear()

with st.spinner("구글 시트에 연결 중..."):
    df, sheet_title, error = load_data()

if error:
    st.error(error)
    st.info("💡 **해결 방법**: 구글 시트에서 `공유` → `sheets-reader@inner-legacy-429605-t1.iam.gserviceaccount.com` 추가 (뷰어 권한)")
elif df is not None:
    st.success(f"✅ 연결 성공! 시트명: **{sheet_title}**")
    st.markdown(f"**데이터 크기:** {len(df)}행 × {len(df.columns)}열")

    st.subheader("📋 컬럼 목록")
    st.write(list(df.columns))

    st.subheader("👀 데이터 미리보기 (상위 10행)")
    st.dataframe(df.head(10), use_container_width=True)

    st.subheader("📈 기본 통계")
    # 숫자형 컬럼만 통계
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        st.dataframe(df[numeric_cols].describe(), use_container_width=True)
    else:
        st.info("숫자형 컬럼이 없습니다.")