from __future__ import annotations

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials as ServiceCredentials
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import jwt
import extra_streamlit_components as stx
from datetime import datetime, timedelta, timezone

# ─────────────────────────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="시래기밥상 매출·지출 분석",
    page_icon="🍲",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────
SPREADSHEET_ID = "1D_s4eh_S1YKHq-jppkNSflfuIa-Eh50MbTOg5caZgF8"
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v2/userinfo"
OAUTH_SCOPES     = "openid email profile"
COOKIE_NAME      = "dashboard_auth"
COOKIE_DAYS      = 7

COLOR_REVENUE = "#3B5BDB"   # 파란색 — 수익
COLOR_EXPENSE = "#FF6B6B"   # 붉은색 — 지출

# ─────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Streamlit 기본 UI 숨기기 */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
div[data-testid="stToolbar"] {visibility: hidden;}
div[data-testid="stDecoration"] {visibility: hidden;}
div[data-testid="stStatusWidget"] {visibility: hidden;}
div[data-testid="stAppViewBlockContainer"] > div:first-child {padding-top: 1rem;}
/* 제목 anchor 링크 숨기기 */
h1 a, h2 a, h3 a { display: none !important; }

/* 카드 스타일 */
.card {
    background: #ffffff;
    border-radius: 16px;
    padding: 24px 28px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    margin-bottom: 16px;
}
.card-title {
    font-size: 16px;
    font-weight: 700;
    color: #212529;
    margin-bottom: 4px;
}
.card-unit {
    font-size: 12px;
    color: #adb5bd;
    float: right;
}
.kpi-label  { font-size: 12px; color: #868e96; margin-bottom: 2px; }
.kpi-value  { font-size: 22px; font-weight: 700; color: #212529; }
.kpi-profit   { font-size: 22px; font-weight: 700; color: #3B5BDB; background:#eef2ff; border-radius:8px; padding:6px 12px; display:block; margin-bottom:4px; }
.kpi-revenue  { font-size: 18px; font-weight: 700; color: #3B5BDB; background:#eef2ff; border-radius:8px; padding:5px 12px; display:block; margin-top:4px; }
.kpi-expense  { font-size: 18px; font-weight: 700; color: #e03131; background:#fff5f5; border-radius:8px; padding:5px 12px; display:block; margin-top:4px; }
.legend-dot-blue  { display:inline-block; width:10px; height:10px; background:#3B5BDB; border-radius:2px; margin-right:6px; }
.legend-dot-gray  { display:inline-block; width:10px; height:10px; background:#ADB5BD; border-radius:2px; margin-right:6px; }
.bottom-label { font-size:13px; color:#495057; font-weight:600; margin-bottom:8px; }
.bottom-row   { display:flex; justify-content:space-between; font-size:13px; padding:4px 0; border-bottom:1px solid #f1f3f5; }
.amt-red   { color:#e03131; font-weight:700; }
.amt-green { color:#2f9e44; font-weight:700; }
.top3-rank { font-size:13px; font-weight:700; color:#adb5bd; width:30px; }
.top3-name { font-size:13px; color:#212529; flex:1; }
.top3-amt  { font-size:13px; font-weight:600; color:#e03131; }
/* 로그인 */
.login-wrap { max-width:420px; margin:80px auto; text-align:center; background:white; border-radius:16px; padding:48px 40px; box-shadow:0 4px 24px rgba(0,0,0,0.1); }
/* metric */
div[data-testid="stMetric"] { background:#f8f9fa; border-radius:12px; padding:16px; }
/* container 카드 스타일 */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: none !important;
    border-radius: 16px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07) !important;
    background: white !important;
    padding: 8px 4px !important;
}
/* 지출 분류 토글 버튼 — 테두리/배경 제거, 텍스트만 */
button[data-testid="baseButton-secondary"][kind="secondary"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #adb5bd !important;
    font-size: 11px !important;
    padding: 2px 4px !important;
    min-height: unset !important;
    height: auto !important;
}
button[data-testid="baseButton-secondary"][kind="secondary"]:hover {
    background: #f1f3f5 !important;
    border-radius: 4px !important;
    color: #495057 !important;
}
/* 상단 두 카드 높이 동일하게 (flex stretch) */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    display: flex;
    flex-direction: column;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] > div,
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] > div > div[data-testid="stVerticalBlock"] {
    flex: 1;
    display: flex;
    flex-direction: column;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] > div > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    flex: 1;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# 쿠키 매니저
# ─────────────────────────────────────────────────────────────────
def get_cm():
    if "cookie_manager" not in st.session_state:
        st.session_state["cookie_manager"] = stx.CookieManager(key="main_cm")
    return st.session_state["cookie_manager"]


# ─────────────────────────────────────────────────────────────────
# JWT
# ─────────────────────────────────────────────────────────────────
def _secret():
    return st.secrets["auth"]["cookie_secret"]

def create_jwt(email: str, name: str) -> str:
    return jwt.encode(
        {"email": email, "name": name,
         "exp": datetime.now(timezone.utc) + timedelta(days=COOKIE_DAYS),
         "iat": datetime.now(timezone.utc)},
        _secret(), algorithm="HS256"
    )

def decode_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# OAuth
# ─────────────────────────────────────────────────────────────────
def build_auth_url():
    from urllib.parse import urlencode
    return f"{GOOGLE_AUTH_URL}?" + urlencode({
        "client_id":     st.secrets["oauth"]["client_id"],
        "redirect_uri":  st.secrets["oauth"]["redirect_uri"],
        "response_type": "code",
        "scope":         OAUTH_SCOPES,
        "access_type":   "offline",
        "prompt":        "select_account",
    })

def exchange_code(code):
    return requests.post(GOOGLE_TOKEN_URL, data={
        "code":          code,
        "client_id":     st.secrets["oauth"]["client_id"],
        "client_secret": st.secrets["oauth"]["client_secret"],
        "redirect_uri":  st.secrets["oauth"]["redirect_uri"],
        "grant_type":    "authorization_code",
    }, timeout=10).json()

def get_user_info(token):
    return requests.get(GOOGLE_USER_URL,
        headers={"Authorization": f"Bearer {token}"}, timeout=10).json()

def _set_session(email, name):
    st.session_state.update({"authenticated": True, "user_email": email, "user_name": name})


# ─────────────────────────────────────────────────────────────────
# 인증
# ─────────────────────────────────────────────────────────────────
def check_auth() -> bool:
    # 개발 모드: 인증 우회
    if st.secrets.get("dev", {}).get("bypass_auth", False):
        _set_session("dev@local", "🛠️ 개발자")
        return True

    cm = get_cm()
    if st.session_state.get("authenticated"):
        return True
    token = cm.get(COOKIE_NAME)
    if token:
        payload = decode_jwt(token)
        if payload and payload.get("email") in list(st.secrets["auth"]["allowed_emails"]):
            _set_session(payload["email"], payload.get("name", payload["email"]))
            return True
        cm.delete(COOKIE_NAME)
    params = st.query_params
    if "code" in params:
        with st.spinner("Google 인증 처리 중..."):
            try:
                td = exchange_code(params["code"])
                if "error" in td:
                    st.error(td.get("error_description", td["error"])); st.stop()
                ui    = get_user_info(td["access_token"])
                email = ui.get("email", "")
                name  = ui.get("name", email)
                if email not in list(st.secrets["auth"]["allowed_emails"]):
                    st.error(f"❌ 접근 권한 없음: `{email}`"); st.stop()
                _set_session(email, name)
                cm.set(COOKIE_NAME, create_jwt(email, name),
                       expires_at=datetime.now(timezone.utc) + timedelta(days=COOKIE_DAYS))
                st.query_params.clear(); st.rerun()
            except Exception as e:
                st.error(f"인증 오류: {e}"); st.stop()
    return False


# ─────────────────────────────────────────────────────────────────
# 데이터 로드 (회계날짜 기준)
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_data() -> pd.DataFrame:
    sa = dict(st.secrets["service_account"])
    creds  = ServiceCredentials.from_service_account_info(sa, scopes=SHEETS_SCOPES)
    client = gspread.authorize(creds)
    ws     = client.open_by_key(SPREADSHEET_ID).worksheet("통합장부")
    df     = pd.DataFrame(ws.get_all_records())

    # 빈 데이터프레임 처리
    if df.empty:
        return pd.DataFrame(columns=["회계날짜", "금액", "유형", "대분류", "중분류",
                                     "연도", "월", "연월"])

    # 컬럼명 앞뒤 공백 제거 (스프레드시트 헤더 오염 방어)
    df.columns = df.columns.str.strip()

    # 필수 컬럼 누락 시 명확한 에러 메시지 제공
    required = ["회계날짜", "금액", "유형", "대분류"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        actual = list(df.columns)
        raise KeyError(
            f"스프레드시트에 필수 컬럼이 없습니다: {missing}\n"
            f"실제 컬럼 목록: {actual}"
        )

    # 회계날짜 기준
    df["회계날짜"] = pd.to_datetime(df["회계날짜"], errors="coerce")
    df["금액"]    = pd.to_numeric(df["금액"], errors="coerce").fillna(0)
    df["연도"]    = df["회계날짜"].dt.year.astype("Int64")
    df["월"]      = df["회계날짜"].dt.month.astype("Int64")
    df["연월"]    = df["회계날짜"].dt.to_period("M").astype(str)
    df["대분류"]  = df["대분류"].replace("", "미분류")

    # 중분류 컬럼 없으면 빈 값으로 생성
    if "중분류" not in df.columns:
        df["중분류"] = ""

    return df


# ─────────────────────────────────────────────────────────────────
# 로그인 화면
# ─────────────────────────────────────────────────────────────────
def show_login():
    st.markdown("""
    <div class="login-wrap">
        <div style="font-size:52px;margin-bottom:12px;">📊</div>
        <h2 style="margin-bottom:6px;">매출 대시보드</h2>
        <p style="color:#868e96;margin-bottom:36px;">허용된 Google 계정으로만 접근 가능합니다.</p>
    </div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        st.link_button("🔑  Google 계정으로 로그인", build_auth_url(),
                       use_container_width=True, type="primary")


# ─────────────────────────────────────────────────────────────────
# 대시보드
# ─────────────────────────────────────────────────────────────────
def show_dashboard():
    is_dev = st.secrets.get("dev", {}).get("bypass_auth", False)
    cm = None if is_dev else get_cm()

    # ── 사이드바 (로그인 정보 + 로그아웃만) ─────────────────────
    with st.sidebar:
        st.markdown(
            f"👤 **{st.session_state.get('user_name','')}**  \n"
            f"<small style='color:#adb5bd'>{st.session_state.get('user_email','')}</small>",
            unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚪 로그아웃", use_container_width=True):
            if cm: cm.delete(COOKIE_NAME)
            st.session_state.clear(); st.rerun()

    # ── 데이터 ────────────────────────────────────────────────
    with st.spinner("데이터 로딩 중..."):
        df = load_data()

    years = sorted(df["연도"].dropna().unique().tolist(), reverse=True)

    # ── 최신 연도/월 기본값 계산 ──────────────────────────────
    latest_year = str(int(years[0])) if years else "전체"
    latest_month_num = (
        df[df["연도"] == int(years[0])]["월"].dropna().max()
        if years else None
    )
    latest_month = f"{int(latest_month_num)}월" if pd.notna(latest_month_num) else "전체"

    year_options  = ["전체"] + [str(int(y)) for y in years]

    # ── 헤더 + 필터 (1줄) ────────────────────────────────────
    h1, h2, h3, h4 = st.columns([5, 1.5, 1.5, 1.5])
    with h1:
        st.markdown(
            '<span style="font-size:20px;font-weight:800;color:#212529;">'
            '🍲 시래기밥상 매출·지출 분석</span>',
            unsafe_allow_html=True)
    with h2:
        sel_year  = st.selectbox("연도", year_options,
                                 index=year_options.index(latest_year),
                                 label_visibility="collapsed")

    # 선택 연도에 따라 실제 데이터가 있는 월만 추출
    if sel_year != "전체":
        avail_months = sorted(
            df[df["연도"] == int(sel_year)]["월"].dropna().unique().tolist()
        )
    else:
        avail_months = sorted(df["월"].dropna().unique().tolist())
    month_options = ["전체"] + [f"{int(m)}월" for m in avail_months]

    # 기본 월값이 새 옵션에 없으면 마지막 월로 fallback
    if latest_month in month_options:
        default_month_idx = month_options.index(latest_month)
    else:
        default_month_idx = len(month_options) - 1  # 마지막 월

    with h3:
        sel_month = st.selectbox("월", month_options,
                                 index=default_month_idx,
                                 label_visibility="collapsed")
    with h4:
        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    period_txt = sel_year if sel_year != "전체" else "전체 기간"
    if sel_month != "전체": period_txt += f" {sel_month}"
    st.markdown("---")

    # ── 필터 적용 ─────────────────────────────────────────────
    fdf = df.copy()
    if sel_year  != "전체": fdf = fdf[fdf["연도"] == int(sel_year)]
    if sel_month != "전체":
        fdf = fdf[fdf["월"] == int(sel_month.replace("월", ""))]

    rev_df = fdf[fdf["유형"] == "매출"]
    exp_df = fdf[fdf["유형"] == "지출"]

    total_rev = rev_df["금액"].sum()
    total_exp = exp_df["금액"].sum()
    net       = total_rev - total_exp
    rate      = round(net / total_rev * 100, 1) if total_rev > 0 else 0.0

    # ── 전월 데이터 계산 ──────────────────────────────────────
    if sel_month != "전체":
        cur_m = int(sel_month.replace("월", ""))
        cur_y = int(sel_year) if sel_year != "전체" else int(latest_year)
        prev_dt = (datetime(cur_y, cur_m, 1) - timedelta(days=1))
        prev_y, prev_m = prev_dt.year, prev_dt.month
        prev_df  = df[(df["연도"] == prev_y) & (df["월"] == prev_m)]
        prev_rev = prev_df[prev_df["유형"] == "매출"]["금액"].sum()
        prev_exp = prev_df[prev_df["유형"] == "지출"]["금액"].sum()
        prev_net = prev_rev - prev_exp
        has_prev = len(prev_df) > 0
    else:
        has_prev = False
        prev_rev = prev_exp = prev_net = 0

    def delta_str(cur, prev):
        """전월 대비 변화량 문자열 반환"""
        if prev == 0:
            return None
        diff = cur - prev
        pct  = diff / abs(prev) * 100
        sign = "▲" if diff >= 0 else "▼"
        color = "#2f9e44" if diff >= 0 else "#e03131"
        return f'<span style="font-size:11px;color:{color};">{sign} {abs(int(diff/10000)):,}만 ({abs(pct):.1f}%)</span>'

    # ── 전월 대비 delta 계산 (KPI 렌더 전에 미리) ────────────
    rev_delta = delta_str(total_rev, prev_rev) if has_prev else ""
    exp_delta = delta_str(total_exp, prev_exp) if has_prev else ""
    net_delta = delta_str(net, prev_net)       if has_prev else ""

    _delta_label = '<span style="font-size:11px;color:#adb5bd;font-weight:400;">전월 대비</span>'
    # 전월 대비 없을 때도 동일 높이 유지 (빈 div로 공간 확보)
    _empty_delta = '<div style="height:20px;margin-top:8px;"></div>'
    net_delta_html = (
        f'<div style="margin-top:8px;height:20px;">{net_delta} {_delta_label}</div>'
        if net_delta else _empty_delta
    )
    rev_delta_html = (
        f'<div style="margin-top:8px;height:20px;">{rev_delta} {_delta_label}</div>'
        if rev_delta else _empty_delta
    )
    exp_delta_html = (
        f'<div style="margin-top:8px;height:20px;">{exp_delta} {_delta_label}</div>'
        if exp_delta else _empty_delta
    )

    # ════════════════════════════════════════════════════════════
    # 1행: KPI 3개 + 도넛 (4열)
    # ════════════════════════════════════════════════════════════
    net_color = "#3B5BDB" if net >= 0 else "#e03131"
    net_bg    = "#eef2ff" if net >= 0 else "#fff5f5"

    # 카드 높이 통일: 고정 min-height + 배경색 제거(숫자만 크게)
    _kpi_label = 'style="font-size:11px;color:#adb5bd;font-weight:600;letter-spacing:0.8px;text-transform:uppercase;margin-bottom:10px;"'
    _kpi_inner = 'style="padding:14px 4px 8px 4px;min-height:120px;"'

    kpi1, kpi2, kpi3, kpi_donut = st.columns([3, 3, 3, 2])

    with kpi1:
        with st.container(border=True):
            st.markdown(
                f'<div {_kpi_inner}>'
                f'<div {_kpi_label}>순이익</div>'
                f'<div style="font-size:32px;font-weight:800;color:{net_color};line-height:1.1;">'
                f'₩{int(net/10000):,}만</div>'
                f'{net_delta_html}'
                f'</div>',
                unsafe_allow_html=True)

    with kpi2:
        with st.container(border=True):
            st.markdown(
                f'<div {_kpi_inner}>'
                f'<div {_kpi_label}>매출</div>'
                f'<div style="font-size:32px;font-weight:800;color:{COLOR_REVENUE};line-height:1.1;">'
                f'₩{int(total_rev/10000):,}만</div>'
                f'{rev_delta_html}'
                f'</div>',
                unsafe_allow_html=True)

    with kpi3:
        with st.container(border=True):
            st.markdown(
                f'<div {_kpi_inner}>'
                f'<div {_kpi_label}>지출</div>'
                f'<div style="font-size:32px;font-weight:800;color:{COLOR_EXPENSE};line-height:1.1;">'
                f'₩{int(total_exp/10000):,}만</div>'
                f'{exp_delta_html}'
                f'</div>',
                unsafe_allow_html=True)

    # ── 도넛 차트 (KPI 행 오른쪽) ────────────────────────────
    with kpi_donut:
        with st.container(border=True):
            donut = go.Figure(go.Pie(
                values=[max(total_rev, 0), max(total_exp, 0)],
                labels=["매출", "지출"],
                hole=0.62,
                marker_colors=[COLOR_REVENUE, COLOR_EXPENSE],
                textinfo="none",
                sort=False,
                direction="clockwise",
                hovertemplate="%{label}: ₩%{value:,.0f}<extra></extra>",
            ))
            donut.update_layout(
                showlegend=False,
                margin=dict(t=4, b=0, l=0, r=0),
                height=130,
                annotations=[dict(
                    text=f"<b>{rate}%</b>",
                    x=0.5, y=0.58, font_size=18,
                    showarrow=False,
                    font_color=net_color,
                ), dict(
                    text="수익률",
                    x=0.5, y=0.38, font_size=10,
                    showarrow=False,
                    font_color="#adb5bd",
                )],
            )
            st.plotly_chart(donut, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                f'<div style="display:flex;justify-content:space-around;font-size:10px;'
                f'color:#868e96;padding-bottom:6px;margin-top:-10px;">'
                f'<span><span style="color:{COLOR_REVENUE};">●</span> {int(total_rev/10000):,}만</span>'
                f'<span><span style="color:{COLOR_EXPENSE};">●</span> {int(total_exp/10000):,}만</span>'
                f'</div>',
                unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    # 2행: 월별 바차트 (전체 너비)
    # ════════════════════════════════════════════════════════════
    with st.container(border=True):

        # 선택 연도 기준 1~12월 전체 (월 필터 무시하고 연도 기준만 적용)
        year_df = df.copy()
        if sel_year != "전체":
            year_df = year_df[year_df["연도"] == int(sel_year)]

        monthly = (
            year_df[year_df["유형"].isin(["매출", "지출"])]
            .groupby(["월", "유형"])["금액"].sum()
            .reset_index()
        )
        # 1~12월 빈 월도 표시
        all_months = pd.DataFrame({"월": list(range(1, 13))})
        for t in ["매출", "지출"]:
            sub = monthly[monthly["유형"] == t][["월", "금액"]]
            sub = all_months.merge(sub, on="월", how="left").fillna(0)
            sub["유형"] = t
            if t == "매출":
                rev_m = sub
            else:
                exp_m = sub
        monthly_full = pd.concat([rev_m, exp_m])
        monthly_full["월라벨"] = monthly_full["월"].astype(str) + "월"
        rev_m["월라벨"] = rev_m["월"].astype(str) + "월"
        exp_m["월라벨"] = exp_m["월"].astype(str) + "월"

        # 선택된 월 강조 표시
        highlight_month = int(sel_month.replace("월", "")) if sel_month != "전체" else None

        # 월별 순이익 계산 (데이터 없는 달은 None으로 처리)
        rev_sorted = rev_m.sort_values("월")
        exp_sorted = exp_m.sort_values("월")
        # 원본 데이터에서 실제 데이터가 있는 월 파악
        has_data_months = set()
        if sel_year != "전체":
            _yd = year_df[year_df["유형"].isin(["매출", "지출"])]
        else:
            _yd = df[df["유형"].isin(["매출", "지출"])]
        has_data_months = set(_yd["월"].dropna().astype(int).unique())

        net_vals = []
        for m, rv, ex in zip(rev_sorted["월"], rev_sorted["금액"], exp_sorted["금액"]):
            if int(m) in has_data_months:
                net_vals.append(rv - ex)
            else:
                net_vals.append(None)

        net_months = pd.DataFrame({
            "월": list(range(1, 13)),
            "순이익": net_vals,
            "월라벨": [f"{m}월" for m in range(1, 13)],
        })

        fig_bar = go.Figure()
        for t, color in [("매출", COLOR_REVENUE), ("지출", COLOR_EXPENSE)]:
            sub = monthly_full[monthly_full["유형"] == t].sort_values("월")
            # 선택월 강조
            if highlight_month:
                opacity = [1.0 if m == highlight_month else 0.4 for m in sub["월"]]
            else:
                opacity = [1.0] * len(sub)
            fig_bar.add_trace(go.Bar(
                x=sub["월라벨"], y=sub["금액"],
                name=t,
                marker_color=color,
                opacity=1.0,
                marker_opacity=opacity if highlight_month else 1.0,
            ))

        # 순이익 라인 (플러스=매출색 파란, 마이너스=지출색 빨간)
        net_colors = [
            COLOR_REVENUE if (v is not None and v >= 0) else COLOR_EXPENSE
            for v in net_months["순이익"]
        ]

        def fmt_man(v):
            """수치를 '만원' 단위 레이블로 변환 (예: -3,068만)"""
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return ""
            m = int(round(float(v) / 10000))
            sign = "+" if m > 0 else ""
            return f"{sign}{m:,}만"

        net_labels = [fmt_man(v) for v in net_months["순이익"]]
        net_label_colors = [
            COLOR_REVENUE if (v is not None and v >= 0) else COLOR_EXPENSE
            for v in net_months["순이익"]
        ]
        net_textpos = [
            "top center" if (v is not None and v >= 0) else "bottom center"
            for v in net_months["순이익"]
        ]

        fig_bar.add_trace(go.Scatter(
            x=net_months["월라벨"],
            y=net_months["순이익"],
            mode="lines+markers+text",
            name="순이익",
            text=net_labels,
            textposition=net_textpos,
            textfont=dict(size=10, color=net_label_colors),
            line=dict(color="rgba(73,80,87,0.55)", width=1.5, dash="dot"),
            marker=dict(
                size=8,
                color=net_colors,
                symbol="circle",
                line=dict(color="white", width=1.5),
            ),
            hovertemplate="순이익: ₩%{y:,.0f}<extra></extra>",
        ))

        # y축 단위: 전량 만원으로 통일
        def fmt_yaxis(v):
            if v == 0:
                return "0"
            return f"{int(v / 10_000):,}만"

        fig_bar.update_layout(
            barmode="group",
            height=290,
            margin=dict(t=10, b=10, l=0, r=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(showgrid=False),
            yaxis=dict(
                showgrid=True, gridcolor="#f1f3f5",
                tickformat=None,
                tickvals=[i * 10_000_000 for i in range(-20, 21)],
                ticktext=[fmt_yaxis(i * 10_000_000) for i in range(-20, 21)],
                zeroline=True, zerolinecolor="#dee2e6", zerolinewidth=1.5,
                autorange=True,
            ),
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # ════════════════════════════════════════════════════════════
    # 하단: 지출 분류 (클릭 선택 → 우측 중분류 드릴다운)
    # ════════════════════════════════════════════════════════════
    DRILL_COLORS = [
        "#3B5BDB","#FF6B6B","#20C997","#FCC419","#845EF7",
        "#F76707","#1C7ED6","#E64980","#37B24D","#F03E3E",
    ]

    # 선택된 대분류 (단일 선택, 클릭 시 우측 드릴다운 표시)
    if "selected_cat" not in st.session_state:
        st.session_state.selected_cat = None

    with st.container(border=True):
        # ── 대분류 집계 ───────────────────────────────────────────
        cat_df = (
            exp_df[~exp_df["대분류"].isin(["미분류", ""])]
            .groupby("대분류")["금액"].sum()
            .reset_index()
            .sort_values("금액", ascending=False)
        )

        total_exp_all  = exp_df["금액"].sum()
        total_cat      = cat_df["금액"].sum() if not cat_df.empty else 0
        unclassified   = total_exp_all - total_cat
        classified_pct = total_cat / total_exp_all * 100 if total_exp_all > 0 else 0

        # ── 헤더 ──────────────────────────────────────────────────
        th1, th2 = st.columns([6, 3])
        with th1:
            st.markdown(
                '<span style="font-size:15px;font-weight:700;">지출 분류</span>'
                '<span style="font-size:12px;color:#adb5bd;margin-left:8px;">'
                '· 대분류 클릭 시 중분류 상세 표시</span>',
                unsafe_allow_html=True)
        with th2:
            st.markdown(
                f'<div style="text-align:right;font-size:12px;color:#adb5bd;padding-top:4px;">'
                f'분류됨 <b style="color:#495057;">{classified_pct:.1f}%</b></div>',
                unsafe_allow_html=True)
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

        # ── 좌(대분류 목록) : 구분선 : 우(중분류 드릴다운) ─────────
        left_col, div_col, right_col = st.columns([5, 0.05, 5])

        # ── 왼쪽: 대분류 목록 ─────────────────────────────────────
        with left_col:
            if cat_df.empty:
                st.markdown('<div style="color:#adb5bd;padding:20px;">분류된 지출 항목이 없습니다.</div>',
                            unsafe_allow_html=True)
            else:
                max_amt = cat_df["금액"].max()
                for i, (_, row) in enumerate(cat_df.iterrows()):
                    is_sel = (row["대분류"] == st.session_state.selected_cat)
                    pct    = row["금액"] / total_exp_all * 100
                    bar_w  = row["금액"] / max_amt * 100
                    color  = DRILL_COLORS[i % len(DRILL_COLORS)]
                    fw     = "700" if is_sel else "500"
                    bg     = f"background:linear-gradient(90deg,{color}14 0%,transparent 100%);border-radius:6px;" if is_sel else ""

                    r_arrow, r_name, r_bar, r_amt, r_pct = st.columns([0.5, 2.4, 5, 1.8, 0.9])
                    with r_arrow:
                        if st.button("›", key=f"cat_{i}", help=f"{row['대분류']} 중분류 보기"):
                            st.session_state.selected_cat = (
                                None if is_sel else row["대분류"]
                            )
                            st.rerun()
                    with r_name:
                        st.markdown(
                            f'<div style="padding:4px 2px;{bg}">'
                            f'<span style="display:inline-block;width:9px;height:9px;'
                            f'background:{color};border-radius:50%;margin-right:7px;vertical-align:middle;"></span>'
                            f'<span style="font-size:13px;font-weight:{fw};color:#212529;">'
                            f'{row["대분류"]}</span></div>',
                            unsafe_allow_html=True)
                    with r_bar:
                        border_s = f"box-shadow:0 0 0 1.5px {color};" if is_sel else ""
                        st.markdown(
                            f'<div style="padding-top:7px;">'
                            f'<div style="background:#f1f3f5;border-radius:6px;height:14px;{border_s}">'
                            f'<div style="background:{color};border-radius:6px;height:14px;'
                            f'width:{bar_w:.1f}%;"></div></div></div>',
                            unsafe_allow_html=True)
                    with r_amt:
                        st.markdown(
                            f'<div style="text-align:right;font-size:13px;font-weight:600;'
                            f'padding-top:5px;">₩{int(row["금액"]/10000):,}만</div>',
                            unsafe_allow_html=True)
                    with r_pct:
                        st.markdown(
                            f'<div style="text-align:right;font-size:13px;font-weight:700;'
                            f'color:#495057;padding-top:5px;">{pct:.1f}%</div>',
                            unsafe_allow_html=True)

        # ── 구분선 ────────────────────────────────────────────────
        with div_col:
            st.markdown(
                '<div style="border-left:1px solid #e9ecef;height:100%;min-height:300px;"></div>',
                unsafe_allow_html=True)

        # ── 오른쪽: 중분류 드릴다운 ───────────────────────────────
        with right_col:
            if st.session_state.selected_cat:
                sel_cat  = st.session_state.selected_cat
                cat_list = list(cat_df.iterrows())
                sel_i    = next(
                    (i for i, (_, r) in enumerate(cat_list) if r["대분류"] == sel_cat), 0
                )
                sel_color = DRILL_COLORS[sel_i % len(DRILL_COLORS)]

                sub_exp = exp_df[exp_df["대분류"] == sel_cat]
                mid_df  = (
                    sub_exp[~sub_exp["중분류"].isin(["미분류", ""])]
                    .groupby("중분류")["금액"].sum()
                    .reset_index()
                    .sort_values("금액", ascending=False)
                )

                # 소제목
                st.markdown(
                    f'<div style="font-size:14px;font-weight:700;margin-bottom:8px;'
                    f'padding-bottom:6px;border-bottom:2px solid {sel_color};">'
                    f'<span style="color:{sel_color};">●</span>'
                    f' {sel_cat} 내역</div>',
                    unsafe_allow_html=True)

                if mid_df.empty:
                    st.markdown(
                        '<div style="color:#adb5bd;font-size:13px;padding:12px 0;">중분류 데이터 없음</div>',
                        unsafe_allow_html=True)
                else:
                    max_mid   = mid_df["금액"].max()
                    total_mid = mid_df["금액"].sum()
                    for _, mrow in mid_df.iterrows():
                        mpct   = mrow["금액"] / total_mid * 100
                        mbar_w = mrow["금액"] / max_mid * 100

                        m1, m2, m3 = st.columns([2.5, 5, 2])
                        with m1:
                            st.markdown(
                                f'<div style="font-size:13px;padding-top:5px;color:#212529;">'
                                f'{mrow["중분류"]}</div>',
                                unsafe_allow_html=True)
                        with m2:
                            st.markdown(
                                f'<div style="padding-top:7px;">'
                                f'<div style="background:#f1f3f5;border-radius:6px;height:14px;">'
                                f'<div style="background:{sel_color};border-radius:6px;height:14px;'
                                f'width:{mbar_w:.1f}%;opacity:0.8;"></div></div></div>',
                                unsafe_allow_html=True)
                        with m3:
                            st.markdown(
                                f'<div style="text-align:right;font-size:13px;padding-top:5px;">'
                                f'₩{int(mrow["금액"]/10000):,}만 '
                                f'<span style="color:#adb5bd;font-size:11px;">({mpct:.1f}%)</span></div>',
                                unsafe_allow_html=True)
            else:
                # 안내 문구
                st.markdown(
                    '<div style="display:flex;align-items:center;justify-content:center;'
                    'height:240px;flex-direction:column;gap:10px;">'
                    '<span style="font-size:32px;opacity:0.3;">←</span>'
                    '<span style="font-size:13px;color:#ced4da;text-align:center;line-height:1.6;">'
                    '대분류를 클릭하면<br>중분류 내역이 표시됩니다</span>'
                    '</div>',
                    unsafe_allow_html=True)

        # ── 미분류 섹션 (전체 너비, 카드 하단) ──────────────────────
        if unclassified > 0:
            unclassified_pct = unclassified / total_exp_all * 100
            unclassified_df = exp_df[exp_df["대분류"].isin(["미분류", ""])]
            unclassified_cnt = len(unclassified_df)

            APPSHEET_URL = (
                "https://www.appsheet.com/start/db3ff1ca-3211-4360-8a02-71747026973b"
                "?platform=desktop#appName=%EC%8B%9C%EB%9E%98%EA%B8%B0%EB%B0%A5%EC%83%81-659360179"
                "&vss=H4sIAAAAAAAAA6WOsQ3CMBREd7naE7hFFAhBA6LBFCb-kSwSO4odILIsMQg9GzBVhsAmIOqI8r-vd3cBZ02XjZfFCXwffteSenAEgW3fkAAXmFnjW1sJMIG1rEc4PG7D8y4QEQ_sa3ty4GGKzP9pZtCKjNelpjYnZS8lfKz0zk4Co4HIUHdeHit6T01GjImVtugcqV2aMbneLcz82kijVlalwFJWjuIL3DphD1sBAAA="
                "&view=%EC%A7%80%EC%B6%9C"
            )

            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            st.markdown('<div style="border-top:1px solid #f1f3f5;margin-bottom:8px;"></div>', unsafe_allow_html=True)

            ban1, ban2 = st.columns([7, 3])
            with ban1:
                st.markdown(
                    f'<div style="margin-bottom:6px;padding:7px 12px;background:#fff9db;'
                    f'border-radius:8px;border-left:3px solid #FCC419;">'
                    f'<span style="font-size:12px;color:#856404;">⚠️ 미분류 </span>'
                    f'<span style="font-size:12px;font-weight:600;color:#856404;">'
                    f'₩{int(unclassified/10000):,}만 ({unclassified_pct:.1f}%)  '
                    f'<span style="font-weight:400;">— {unclassified_cnt}건</span></span>'
                    f'</div>',
                    unsafe_allow_html=True)
            with ban2:
                st.link_button(
                    "📝 AppSheet에서 분류하기 →",
                    APPSHEET_URL,
                    use_container_width=True,
                )

            # 미분류 항목 테이블
            with st.expander(f"미분류 항목 보기 ({unclassified_cnt}건)", expanded=False):
                show_cols = [c for c in ["거래날짜", "결제수단", "보냄", "금액", "내용"] if c in unclassified_df.columns]
                tbl = (
                    unclassified_df[show_cols]
                    .sort_values("금액", ascending=False)
                    .reset_index(drop=True)
                )
                # object 컬럼의 혼합 타입(int/str) → 강제 str 변환
                for _c in tbl.select_dtypes(include="object").columns:
                    tbl[_c] = tbl[_c].astype(str)
                st.dataframe(
                    tbl,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "금액": st.column_config.NumberColumn("금액", format="₩%d"),
                    },
                )

# ─────────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────────
def main():
    if check_auth():
        show_dashboard()
    else:
        show_login()

main()