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
    page_title="매출 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
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
    ws     = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    df     = pd.DataFrame(ws.get_all_records())

    # 회계날짜 기준
    df["회계날짜"] = pd.to_datetime(df["회계날짜"], errors="coerce")
    df["금액"]    = pd.to_numeric(df["금액"], errors="coerce").fillna(0)
    df["연도"]    = df["회계날짜"].dt.year.astype("Int64")
    df["월"]      = df["회계날짜"].dt.month.astype("Int64")
    df["연월"]    = df["회계날짜"].dt.to_period("M").astype(str)
    df["대분류"]  = df["대분류"].replace("", "미분류")
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
        auth_url = build_auth_url()
        st.markdown(
            f'<a href="{auth_url}" target="_self" style="'
            f'display:block;width:100%;padding:10px 0;text-align:center;'
            f'background:#3B5BDB;color:white;border-radius:8px;font-size:15px;'
            f'font-weight:600;text-decoration:none;cursor:pointer;">'
            f'🔑&nbsp;&nbsp;Google 계정으로 로그인</a>',
            unsafe_allow_html=True)


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

    # ── 헤더 + 필터 ───────────────────────────────────────────
    h1, h2, h3, h4 = st.columns([4, 2, 2, 1.5])
    with h1:
        st.title("📊 매출 대시보드")
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

    period = sel_year if sel_year != "전체" else "전체 기간"
    if sel_month != "전체": period += f" {sel_month}"
    st.caption(f"📅 {period}  |  기준: 회계날짜  |  업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
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

    # ════════════════════════════════════════════════════════════
    # 상단 카드: 도넛 + 월별 바차트
    # ════════════════════════════════════════════════════════════
    col_left, col_right = st.columns([4, 6])

    # ── 도넛 + KPI ────────────────────────────────────────────
    with col_left:
      with st.container(border=True):
        ct1, ct2 = st.columns([1, 1])
        with ct1:
            period_label = f"{sel_month} " if sel_month != "전체" else ""
            st.markdown(f'<span class="card-title">{period_label}수익 · 지출 CHART</span>', unsafe_allow_html=True)
        with ct2:
            st.markdown('<div style="text-align:right;color:#adb5bd;font-size:12px;padding-top:4px;">단위 : 원 (₩)</div>', unsafe_allow_html=True)

        # 도넛 차트
        donut = go.Figure(go.Pie(
            values=[total_rev, total_exp],
            labels=["수익", "지출"],
            hole=0.62,
            marker_colors=[COLOR_REVENUE, COLOR_EXPENSE],
            textinfo="none",
            sort=False,
            direction="clockwise",
            hovertemplate="%{label}: ₩%{value:,.0f}<extra></extra>",
        ))
        donut.update_layout(
            showlegend=False,
            margin=dict(t=0, b=0, l=0, r=0),
            height=160,
            annotations=[dict(
                text=f"<b>{rate}%</b>",
                x=0.5, y=0.5, font_size=20,
                showarrow=False, font_color="#212529"
            )],
        )
        # KPI 왼쪽 + 도넛 오른쪽
        k1, k2 = st.columns([1, 1])
        with k1:
            st.markdown(f"""
            <div style="padding-top:12px; padding-bottom:35px;">
                <div class="kpi-label">💰 순이익(수익-지출)</div>
                <div class="kpi-profit">₩{net:,.0f}</div>
                <div style="margin-top:14px;">
                    <div style="font-size:12px;color:#868e96;">
                        <span class="legend-dot-blue"></span>수익
                    </div>
                    <span class="kpi-revenue">₩{total_rev:,.0f}</span>
                </div>
                <div style="margin-top:10px;">
                    <div style="font-size:12px;color:#868e96;">
                        <span class="legend-dot-gray"></span>지출
                    </div>
                    <span class="kpi-expense">₩{total_exp:,.0f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with k2:
            st.markdown('<div style="height:48px"></div>', unsafe_allow_html=True)
            st.plotly_chart(donut, use_container_width=True, config={"displayModeBar": False})

    # ── 월별 바차트 ────────────────────────────────────────────
    with col_right:
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

        fig_bar.update_layout(
            barmode="group",
            height=290,
            margin=dict(t=10, b=10, l=0, r=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(showgrid=False),
            yaxis=dict(
                showgrid=True, gridcolor="#f1f3f5", tickformat=",.0f",
                zeroline=True, zerolinecolor="#dee2e6", zerolinewidth=1.5,
            ),
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # ════════════════════════════════════════════════════════════
    # 하단 카드: 지출 드릴다운 (대분류 → 중분류)
    # ════════════════════════════════════════════════════════════
    DRILL_COLORS = [
        "#3B5BDB","#FF6B6B","#20C997","#FCC419","#845EF7",
        "#F76707","#1C7ED6","#E64980","#37B24D","#F03E3E",
    ]

    if "drill_category" not in st.session_state:
        st.session_state.drill_category = None

    with st.container(border=True):
        # ── 헤더 ──────────────────────────────────────────────────
        st.markdown('<span style="font-size:15px;font-weight:700;">지출 분류</span>',
                    unsafe_allow_html=True)
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

        # ── 대분류 집계 ───────────────────────────────────────────
        cat_df = (
            exp_df[~exp_df["대분류"].isin(["미분류", ""])]
            .groupby("대분류")["금액"].sum()
            .reset_index()
            .sort_values("금액", ascending=False)
        )

        if cat_df.empty:
            st.markdown('<div style="color:#adb5bd;padding:20px;">분류된 지출 항목이 없습니다.</div>',
                        unsafe_allow_html=True)
        else:
            total_exp_all = exp_df["금액"].sum()          # 미분류 포함 전체 지출
            total_cat     = cat_df["금액"].sum()          # 분류된 항목 합계
            max_amt       = cat_df["금액"].max()          # 막대 길이 기준
            unclassified  = total_exp_all - total_cat     # 미분류 금액
            classified_pct = total_cat / total_exp_all * 100 if total_exp_all > 0 else 0

            # ── 좌우 2분할 ────────────────────────────────────────
            left_col, divider_col, right_col = st.columns([9, 0.05, 9])

            # ── 왼쪽: 대분류 ─────────────────────────────────────
            with left_col:
                hdr1, hdr2 = st.columns([5, 3])
                with hdr1:
                    st.markdown('<div style="font-size:12px;color:#adb5bd;">대분류 · 항목을 클릭하면 중분류 표시</div>',
                                unsafe_allow_html=True)
                with hdr2:
                    st.markdown(
                        f'<div style="text-align:right;font-size:12px;color:#adb5bd;">'
                        f'분류됨 <b style="color:#495057;">{classified_pct:.1f}%</b></div>',
                        unsafe_allow_html=True)
                for i, (_, row) in enumerate(cat_df.iterrows()):
                    pct      = row["금액"] / total_exp_all * 100   # 총 지출 기준
                    bar_w    = row["금액"] / max_amt * 100
                    color    = DRILL_COLORS[i % len(DRILL_COLORS)]
                    selected = (st.session_state.drill_category == row["대분류"])

                    c_dot, c_btn, c_bar, c_amt, c_pct = st.columns([0.3, 1.8, 5, 1.5, 0.8])
                    with c_dot:
                        st.markdown(
                            f'<div style="width:12px;height:12px;background:{color};'
                            f'border-radius:3px;margin-top:9px;"></div>',
                            unsafe_allow_html=True)
                    with c_btn:
                        if st.button(row["대분류"], key=f"drill_{i}", use_container_width=True):
                            st.session_state.drill_category = (
                                None if selected else row["대분류"]
                            )
                            st.rerun()
                    with c_bar:
                        bar_color = color if not selected else color
                        border    = f"box-shadow:0 0 0 2px {color};" if selected else ""
                        st.markdown(
                            f'<div style="padding-top:7px;">'
                            f'<div style="background:#f1f3f5;border-radius:6px;height:18px;width:100%;{border}">'
                            f'<div style="background:{color};border-radius:6px;height:18px;'
                            f'width:{bar_w:.1f}%;"></div>'
                            f'</div></div>',
                            unsafe_allow_html=True)
                    with c_amt:
                        st.markdown(
                            f'<div style="text-align:right;font-size:13px;font-weight:600;'
                            f'padding-top:6px;">₩{int(row["금액"]/10000):,}만</div>',
                            unsafe_allow_html=True)
                    with c_pct:
                        st.markdown(
                            f'<div style="text-align:right;font-size:14px;font-weight:600;color:#495057;'
                            f'padding-top:5px;">{pct:.1f}%</div>',
                            unsafe_allow_html=True)

                # 미분류 안내 문구 (미분류가 있을 때만)
                if unclassified > 0:
                    unclassified_pct = unclassified / total_exp_all * 100
                    st.markdown(
                        f'<div style="margin-top:10px;margin-bottom:14px;padding:7px 12px;background:#fff9db;'
                        f'border-radius:8px;border-left:3px solid #FCC419;">'
                        f'<span style="font-size:12px;color:#856404;">⚠️ 미분류 </span>'
                        f'<span style="font-size:12px;font-weight:600;color:#856404;">'
                        f'₩{int(unclassified/10000):,}만 ({unclassified_pct:.1f}%)</span>'
                        f'<span style="font-size:11px;color:#adb5bd;margin-left:6px;">— 분류 개선 필요</span>'
                        f'</div>',
                        unsafe_allow_html=True)

            # ── 구분선 ────────────────────────────────────────────
            with divider_col:
                st.markdown(
                    '<div style="border-left:1px solid #e9ecef;height:100%;min-height:300px;"></div>',
                    unsafe_allow_html=True)

            # ── 오른쪽: 중분류 ────────────────────────────────────
            with right_col:
                if not st.session_state.drill_category:
                    st.markdown(
                        '<div style="display:flex;align-items:center;justify-content:center;'
                        'height:200px;color:#ced4da;font-size:14px;">← 대분류를 선택하세요</div>',
                        unsafe_allow_html=True)
                else:
                    sel_color_idx = next(
                        (i for i, (_, r) in enumerate(cat_df.iterrows())
                         if r["대분류"] == st.session_state.drill_category), 0
                    )
                    sel_color = DRILL_COLORS[sel_color_idx % len(DRILL_COLORS)]

                    st.markdown(
                        f'<div style="font-size:12px;color:#adb5bd;margin-bottom:4px;">'
                        f'<span style="font-weight:700;color:{sel_color};">'
                        f'{st.session_state.drill_category}</span> · 중분류</div>',
                        unsafe_allow_html=True)

                    sub_exp = exp_df[exp_df["대분류"] == st.session_state.drill_category]
                    mid_df  = (
                        sub_exp[~sub_exp["중분류"].isin(["미분류", ""])]
                        .groupby("중분류")["금액"].sum()
                        .reset_index()
                        .sort_values("금액", ascending=False)
                    )

                    if mid_df.empty:
                        st.markdown('<div style="color:#adb5bd;font-size:13px;padding:8px 0;">중분류 데이터가 없습니다.</div>',
                                    unsafe_allow_html=True)
                    else:
                        total_mid = mid_df["금액"].sum()
                        max_mid   = mid_df["금액"].max()

                        for j, (_, mrow) in enumerate(mid_df.iterrows()):
                            mpct   = mrow["금액"] / total_mid * 100
                            mbar_w = mrow["금액"] / max_mid * 100
                            mc_dot, mc_name, mc_bar, mc_amt, mc_pct = st.columns([0.3, 1.8, 5, 1.5, 0.8])
                            with mc_dot:
                                st.markdown(
                                    f'<div style="width:10px;height:10px;background:{sel_color};'
                                    f'border-radius:2px;margin-top:9px;"></div>',
                                    unsafe_allow_html=True)
                            with mc_name:
                                st.markdown(
                                    f'<div style="font-size:13px;font-weight:500;padding-top:6px;">'
                                    f'{mrow["중분류"]}</div>',
                                    unsafe_allow_html=True)
                            with mc_bar:
                                st.markdown(
                                    f'<div style="padding-top:7px;">'
                                    f'<div style="background:#f1f3f5;border-radius:6px;height:16px;width:100%;">'
                                    f'<div style="background:{sel_color};border-radius:6px;height:16px;'
                                    f'width:{mbar_w:.1f}%;opacity:0.8;"></div>'
                                    f'</div></div>',
                                    unsafe_allow_html=True)
                            with mc_amt:
                                st.markdown(
                                    f'<div style="text-align:right;font-size:13px;font-weight:600;'
                                    f'padding-top:6px;">₩{int(mrow["금액"]/10000):,}만</div>',
                                    unsafe_allow_html=True)
                            with mc_pct:
                                st.markdown(
                                    f'<div style="text-align:right;font-size:12px;color:#868e96;'
                                    f'padding-top:6px;">{mpct:.1f}%</div>',
                                    unsafe_allow_html=True)




# ─────────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────────
def main():
    if check_auth():
        show_dashboard()
    else:
        show_login()

main()