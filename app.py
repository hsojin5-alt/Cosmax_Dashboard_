import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import colorsys

st.set_page_config(page_title="효능원료 안정도 종합 대시보드", layout="wide")

# ── CSS 스타일 ───────────────────────────────────────────────
st.markdown("""
<style>
    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] {
        background-color: #1a1a2e;
    }
    section[data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    section[data-testid="stSidebar"] .stMultiSelect span[data-baseweb="tag"] {
        background-color: #e74c6f;
    }

    /* 헤더 카드 */
    .header-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 28px 32px 18px 32px;
        margin-bottom: 16px;
    }
    .header-title {
        color: #fff;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .header-sub {
        color: #b0b8c8;
        font-size: 14px;
        margin-bottom: 0;
    }

    /* KPI 카드 */
    .kpi-container {
        display: flex;
        gap: 12px;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
    .kpi-card {
        background: #fff;
        border-radius: 12px;
        padding: 16px 20px;
        flex: 1;
        min-width: 130px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        text-align: center;
    }
    .kpi-label {
        color: #888;
        font-size: 12px;
        margin-bottom: 4px;
    }
    .kpi-value {
        color: #1a1a2e;
        font-size: 26px;
        font-weight: 700;
    }
    .kpi-unit {
        color: #aaa;
        font-size: 12px;
    }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: #f5f5fa;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #fff;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
    }

    /* 서브헤더 */
    .section-header {
        font-size: 20px;
        font-weight: 700;
        color: #1a1a2e;
        margin: 24px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #e8e8f0;
    }
</style>
""", unsafe_allow_html=True)


# ── 데이터 로드 ──────────────────────────────────────────────
@st.cache_data
def load_data(file_bytes):
    xls = pd.ExcelFile(file_bytes)

    raw = pd.read_excel(xls, sheet_name="원료베이스", header=None)
    raw.columns = ["구분", "효능", "원료명", "주요성분", "원료함량"]
    raw = raw.iloc[1:].reset_index(drop=True)
    raw["원료함량"] = pd.to_numeric(raw["원료함량"], errors="coerce")

    sol = pd.read_excel(xls, sheet_name="가용화표준품안정도", header=None)
    sol.columns = [
        "구분", "효능", "주요성분", "비중",
        "즉_pH25", "1D_pH25", "1W_pH25",
        "1M_pH4", "1M_pH25", "1M_pH37", "1M_pH45", "1M_광",
        "2M_pH4", "2M_pH25", "2M_pH37", "2M_pH45", "2M_광",
        "3M_pH4", "3M_pH25", "3M_pH37", "3M_pH45", "3M_광",
    ]
    sol = sol.iloc[2:].reset_index(drop=True)
    for c in sol.columns[3:]:
        sol[c] = pd.to_numeric(sol[c], errors="coerce")

    emu = pd.read_excel(xls, sheet_name="유화 표준품 안정도", header=None)
    emu.columns = [
        "구분", "효능", "주요성분", "비중",
        "즉_pH25", "즉_점도", "1D_pH25", "1D_점도", "1W_pH25", "1W_점도",
        "1M_pH4", "1M_pH25", "1M_pH37", "1M_pH45", "1M_광", "1M_점도",
        "2M_pH4", "2M_pH25", "2M_pH37", "2M_pH45", "2M_광", "2M_점도",
        "3M_pH4", "3M_pH25", "3M_pH37", "3M_pH45", "3M_광", "3M_점도",
    ]
    emu = emu.iloc[2:].reset_index(drop=True)
    for c in emu.columns[3:]:
        emu[c] = pd.to_numeric(emu[c], errors="coerce")
    ph_cols = [c for c in emu.columns if "pH" in c]
    for c in ph_cols:
        emu[c] = emu[c].apply(lambda v: v / 100 if pd.notna(v) and v > 14 else v)

    return raw, sol, emu

# ── 공통 설정 ────────────────────────────────────────────────
효능순서 = ["미백", "보습", "탄력", "진정", "모공", "기능성"]
색상맵 = {"미백": "#FF6B6B", "보습": "#4ECDC4", "탄력": "#45B7D1",
         "진정": "#96CEB4", "모공": "#FFEAA7", "기능성": "#DDA0DD"}

_효능_hsl = {
    "미백": (0.0, 0.80, 0.55),
    "보습": (0.50, 0.70, 0.45),
    "탄력": (0.60, 0.75, 0.50),
    "진정": (0.35, 0.55, 0.45),
    "모공": (0.12, 0.85, 0.55),
}


def hsl_to_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def build_color_map(valid_df, 효능리스트):
    그룹 = {}
    for eff in 효능리스트:
        그룹[eff] = valid_df[valid_df["효능"] == eff]["주요성분"].tolist()
    cmap = {}
    for eff in 효능리스트:
        h, s, l = _효능_hsl[eff]
        members = 그룹[eff]
        n = len(members)
        for i, ing in enumerate(members):
            if n == 1:
                nl, ns = l, s
            else:
                nl = 0.30 + 0.40 * i / (n - 1)
                ns = max(0.45, s - 0.15 * i / (n - 1))
            cmap[ing] = hsl_to_hex(h, ns, nl)
    return 그룹, cmap


# ── 사이드바 필터 ────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙ 필터 설정")
    st.markdown("---")

    st.markdown("**파일 업로드**")
    uploaded_file = st.file_uploader(
        "엑셀 파일 업로드", type=["xlsx", "xls"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown("**구분**")
    sel_구분 = st.multiselect(
        "구분 선택", ["가용화", "유화"], default=["가용화", "유화"],
        key="filter_gubun", label_visibility="collapsed",
    )

    st.markdown("**효능**")
    sel_효능 = st.multiselect(
        "효능 선택", 효능순서, default=효능순서,
        key="filter_eff", label_visibility="collapsed",
    )

# ── 헤더 ─────────────────────────────────────────────────────
st.markdown("""
<div class="header-card">
    <p class="header-title">🧪 효능원료 안정도 종합 대시보드</p>
    <p class="header-sub">원료 베이스 · 가용화 안정도 · 유화 안정도 데이터를 한눈에 확인하세요.</p>
</div>
""", unsafe_allow_html=True)

# ── 파일 업로드 체크 ─────────────────────────────────────────
if uploaded_file is None:
    st.info("👈 왼쪽 사이드바에서 엑셀 파일(.xlsx)을 업로드해주세요.")
    st.stop()

raw, sol, emu = load_data(uploaded_file)

# ── KPI 카드 ─────────────────────────────────────────────────
raw_가 = raw[raw["구분"] == "가용화"]
raw_유 = raw[raw["구분"] == "유화"]
sol_valid = sol.dropna(subset=["비중"])
emu_valid = emu.dropna(subset=["비중"])

kpi_data = [
    ("가용화 원료", f"{len(raw_가)}", "종"),
    ("유화 원료", f"{len(raw_유)}", "종"),
    ("가용화 안정도", f"{len(sol_valid)}", "건"),
    ("유화 안정도", f"{len(emu_valid)}", "건"),
    ("평균 비중 (가용화)", f"{sol_valid['비중'].mean():.4f}", ""),
    ("평균 비중 (유화)", f"{emu_valid['비중'].mean():.4f}", ""),
]

kpi_html = '<div class="kpi-container">'
for label, value, unit in kpi_data:
    kpi_html += f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-unit">{unit}</div>
    </div>"""
kpi_html += "</div>"
st.markdown(kpi_html, unsafe_allow_html=True)

# ── 탭 구성 ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 원료 베이스", "🧫 가용화 안정도", "🧴 유화 안정도", "📋 원본 데이터"])

# ═══════════════════════════════════════════════════════════════
# 탭1: 원료 베이스
# ═══════════════════════════════════════════════════════════════
with tab1:
    raw_filtered = raw[raw["구분"].isin(sel_구분) & raw["효능"].isin(sel_효능)]

    # 파이 차트
    pie_cols = st.columns(2)
    for idx, (label, subset) in enumerate([
        ("가용화", raw_filtered[raw_filtered["구분"] == "가용화"]),
        ("유화", raw_filtered[raw_filtered["구분"] == "유화"]),
    ]):
        if label not in sel_구분:
            continue
        with pie_cols[idx]:
            total = len(subset)
            count = subset.groupby("효능").size().reindex(
                [e for e in 효능순서 if e in sel_효능], fill_value=0
            ).reset_index()
            count.columns = ["효능", "원료수"]
            fig = px.pie(
                count, names="효능", values="원료수",
                title=f"{label} - 효능별 원료 수 (총 {total}개)",
                hole=0.4, color="효능", color_discrete_map=색상맵,
                category_orders={"효능": 효능순서},
            )
            fig.update_traces(sort=False)
            fig.update_layout(height=320, margin=dict(t=50, b=20))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">원료함량 비교</div>', unsafe_allow_html=True)
    for label, subset in [
        ("가용화", raw_filtered[raw_filtered["구분"] == "가용화"]),
        ("유화", raw_filtered[raw_filtered["구분"] == "유화"]),
    ]:
        if label not in sel_구분 or subset.empty:
            continue
        subset = subset.copy()
        subset["효능"] = pd.Categorical(subset["효능"], categories=효능순서, ordered=True)
        subset = subset.sort_values("효능")
        fig = px.bar(
            subset, x="원료명", y="원료함량", color="효능",
            title=f"{label} - 원료함량(%)",
            category_orders={"효능": 효능순서}, color_discrete_map=색상맵,
        )
        fig.update_layout(
            height=450, xaxis_tickangle=-45, xaxis_tickfont_size=8,
            xaxis_title="", yaxis_title="원료함량(%)", legend_title="효능",
            margin=dict(t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# 공통 안정도 차트 생성 함수
# ═══════════════════════════════════════════════════════════════
def render_stability_tab(valid_df, filtered_df, 효능그룹, color_map,
                         효능리스트, selected_effs, time_cols, time_labels,
                         visc_cols=None, light_cols=None, prefix="",
                         ph_range=None):
    if ph_range is None:
        ph_range = [3, 7.5]
    # 25℃ pH 변화
    st.markdown('<div class="section-header">25℃ pH 변화 비교</div>', unsafe_allow_html=True)
    fig = go.Figure()
    for eff in 효능리스트:
        if eff not in selected_effs:
            continue
        for ing in 효능그룹[eff]:
            rd = filtered_df[filtered_df["주요성분"] == ing]
            if rd.empty:
                continue
            row = rd.iloc[0]
            fig.add_trace(go.Scatter(
                x=time_labels, y=[row[c] for c in time_cols],
                mode="lines+markers", name=ing,
                legendgroup=eff, legendgrouptitle_text=eff,
                line=dict(color=color_map[ing]),
                marker=dict(color=color_map[ing]),
            ))
    fig.update_layout(
        xaxis_title="측정 시점", yaxis_title="pH", yaxis_range=ph_range,
        height=500, legend=dict(font_size=9, groupclick="toggleitem",
                                tracegroupgap=5, itemsizing="constant"),
        margin=dict(r=250, t=30),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 점도 (유화만)
    if visc_cols:
        st.markdown('<div class="section-header">점도 경시 변화</div>', unsafe_allow_html=True)
        fig_v = go.Figure()
        for eff in 효능리스트:
            if eff not in selected_effs:
                continue
            for ing in 효능그룹[eff]:
                rd = filtered_df[filtered_df["주요성분"] == ing]
                if rd.empty:
                    continue
                row = rd.iloc[0]
                vals = [row[c] for c in visc_cols]
                if any(pd.notna(v) for v in vals):
                    fig_v.add_trace(go.Scatter(
                        x=time_labels, y=vals, mode="lines+markers", name=ing,
                        legendgroup=eff, legendgrouptitle_text=eff,
                        line=dict(color=color_map[ing]),
                        marker=dict(color=color_map[ing]),
                    ))
        fig_v.update_layout(
            xaxis_title="측정 시점", yaxis_title="점도 (cP)",
            height=500, legend=dict(font_size=9, groupclick="toggleitem",
                                    tracegroupgap=5, itemsizing="constant"),
            margin=dict(r=250, t=30),
        )
        st.plotly_chart(fig_v, use_container_width=True)

    # 3M 온도별 pH + 광 안정도
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('<div class="section-header">3개월 시점 - 온도별 pH</div>', unsafe_allow_html=True)
        temp_labels = ["4℃", "25℃", "37℃", "45℃"]
        fig2 = go.Figure()
        for eff in 효능리스트:
            if eff not in selected_effs:
                continue
            for ing in 효능그룹[eff]:
                rd = filtered_df[filtered_df["주요성분"] == ing]
                if rd.empty:
                    continue
                row = rd.iloc[0]
                fig2.add_trace(go.Bar(
                    name=ing, x=temp_labels,
                    y=[row[c] for c in ["3M_pH4", "3M_pH25", "3M_pH37", "3M_pH45"]],
                    legendgroup=eff, legendgrouptitle_text=eff,
                    marker_color=color_map[ing],
                ))
        fig2.update_layout(
            barmode="group", yaxis_range=ph_range, height=450,
            legend=dict(font_size=8, groupclick="toggleitem",
                        tracegroupgap=3, itemsizing="constant"),
            margin=dict(t=30),
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_right:
        if light_cols:
            st.markdown('<div class="section-header">광 안정도 (1M / 2M / 3M)</div>', unsafe_allow_html=True)
            hm_df = filtered_df.set_index("주요성분")[light_cols].dropna()
            hm_df.columns = ["1M", "2M", "3M"]
            if not hm_df.empty:
                fig3 = px.imshow(
                    hm_df, text_auto=".2f", aspect="auto",
                    color_continuous_scale=[[0, "#f48fb1"], [0.5, "#81d4fa"], [1, "#a5d6a7"]],
                    labels=dict(x="측정 시점", y="성분", color="pH"),
                )
                fig3.update_layout(height=450, margin=dict(t=30))
                st.plotly_chart(fig3, use_container_width=True)

    # 비중 비교
    st.markdown('<div class="section-header">원료별 비중 비교</div>', unsafe_allow_html=True)
    비중_df = filtered_df[["효능", "주요성분", "비중"]].copy()
    비중_df["효능"] = pd.Categorical(비중_df["효능"], categories=효능리스트, ordered=True)
    비중_df = 비중_df.sort_values("효능")
    fig_sg = go.Figure()
    for eff in 효능리스트:
        if eff not in selected_effs:
            continue
        sub = 비중_df[비중_df["효능"] == eff]
        for _, row in sub.iterrows():
            fig_sg.add_trace(go.Bar(
                name=row["주요성분"], x=[row["주요성분"]], y=[row["비중"]],
                marker_color=color_map[row["주요성분"]],
                legendgroup=eff, legendgrouptitle_text=eff,
                text=[f"{row['비중']:.4f}"], textposition="outside",
            ))
    fig_sg.update_layout(
        height=450, xaxis_tickangle=-45, xaxis_tickfont_size=9,
        xaxis_title="", yaxis_title="비중",
        legend=dict(font_size=9, groupclick="toggleitem",
                    tracegroupgap=5, itemsizing="constant"),
        margin=dict(r=250, t=30),
    )
    st.plotly_chart(fig_sg, use_container_width=True)

    # 점도 변화율 (유화만)
    if visc_cols:
        st.markdown('<div class="section-header">점도 변화율 (즉시 대비 3M)</div>', unsafe_allow_html=True)
        vc = []
        for _, row in filtered_df.iterrows():
            if pd.notna(row["즉_점도"]) and pd.notna(row["3M_점도"]) and row["즉_점도"] != 0:
                ch = (row["3M_점도"] - row["즉_점도"]) / row["즉_점도"] * 100
                vc.append({"주요성분": row["주요성분"], "효능": row["효능"], "변화율(%)": ch})
        if vc:
            vc_df = pd.DataFrame(vc).sort_values("변화율(%)")
            fig7 = go.Figure()
            for _, r in vc_df.iterrows():
                fig7.add_trace(go.Bar(
                    name=r["주요성분"], x=[r["변화율(%)"]], y=[r["주요성분"]],
                    orientation="h",
                    marker_color=color_map.get(r["주요성분"], "#888"),
                    legendgroup=r["효능"], legendgrouptitle_text=r["효능"],
                    text=[f"{r['변화율(%)']:.1f}%"], textposition="outside",
                ))
            fig7.update_layout(
                height=400, xaxis_title="변화율(%)", yaxis_tickfont_size=9,
                legend=dict(font_size=9, groupclick="toggleitem",
                            tracegroupgap=5, itemsizing="constant"),
                margin=dict(t=30),
            )
            st.plotly_chart(fig7, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# 탭2: 가용화 안정도
# ═══════════════════════════════════════════════════════════════
with tab2:
    sol_eff_list = [e for e in ["미백", "보습", "탄력", "진정", "모공"] if e in sel_효능]
    sol_filtered = sol_valid[sol_valid["효능"].isin(sol_eff_list)]
    sol_그룹, sol_cmap = build_color_map(sol_valid, sol_eff_list)

    render_stability_tab(
        sol_valid, sol_filtered, sol_그룹, sol_cmap, sol_eff_list, sol_eff_list,
        time_cols=["즉_pH25", "1D_pH25", "1W_pH25", "1M_pH25", "2M_pH25", "3M_pH25"],
        time_labels=["즉시", "1D", "1W", "1M", "2M", "3M"],
        light_cols=["1M_광", "2M_광", "3M_광"],
    )

# ═══════════════════════════════════════════════════════════════
# 탭3: 유화 안정도
# ═══════════════════════════════════════════════════════════════
with tab3:
    emu_eff_list = [e for e in ["미백", "보습", "탄력", "진정", "모공"] if e in sel_효능]
    emu_filtered = emu_valid[emu_valid["효능"].isin(emu_eff_list)]
    emu_그룹, emu_cmap = build_color_map(emu_valid, emu_eff_list)

    render_stability_tab(
        emu_valid, emu_filtered, emu_그룹, emu_cmap, emu_eff_list, emu_eff_list,
        time_cols=["즉_pH25", "1D_pH25", "1W_pH25", "1M_pH25", "2M_pH25", "3M_pH25"],
        time_labels=["즉시", "1D", "1W", "1M", "2M", "3M"],
        visc_cols=["즉_점도", "1D_점도", "1W_점도", "1M_점도", "2M_점도", "3M_점도"],
        light_cols=["1M_광", "2M_광", "3M_광"],
        ph_range=[5, 7.5],
    )

# ═══════════════════════════════════════════════════════════════
# 탭4: 원본 데이터
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">원료 베이스</div>', unsafe_allow_html=True)
    st.dataframe(raw, use_container_width=True, height=300)

    st.markdown('<div class="section-header">가용화 표준품 안정도</div>', unsafe_allow_html=True)
    st.dataframe(sol, use_container_width=True, height=300)

    st.markdown('<div class="section-header">유화 표준품 안정도</div>', unsafe_allow_html=True)
    st.dataframe(emu, use_container_width=True, height=300)
