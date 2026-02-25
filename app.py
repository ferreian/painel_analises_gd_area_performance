import streamlit as st
import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# ── Configuração da página ───────────────────────────────
st.set_page_config(layout="wide", page_title="Dashboard GD - Stine")

# ── Inicializa session state ─────────────────────────────
if "limpar" not in st.session_state:
    st.session_state["limpar"] = False
if "sel_cultura" not in st.session_state:
    st.session_state["sel_cultura"] = "Todos"
if "sel_safra" not in st.session_state:
    st.session_state["sel_safra"] = "Todos"
if "pagina" not in st.session_state:
    st.session_state["pagina"] = "areas"

# ── Credenciais ──────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
except Exception:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# ── Paleta Stine ─────────────────────────────────────────
COR_MILHO     = "#005FAE"
COR_SOJA      = "#009D57"
AZUIS         = ["#87C2EB", "#2581C4", "#004F9F", "#023064"]
VERDES        = ["#ABD084", "#72BA65", "#23A638", "#11811C"]
STINE_PALETTE = [COR_MILHO, COR_SOJA] + AZUIS + VERDES

# ── Cores gráficos ───────────────────────────────────────
cores_status = {
    "Com Resultado":       "#7ED321",
    "Aguardando Colheita": "#4A90D9",
    "Não Definido":        "#9E9E9E"
}
cores_mix = {
    "STINE":        "#7ED321",
    "Concorrência": "#4A90D9"
}
cores_cultura = {
    "Milho": "#005FAE",
    "Soja":  "#009D57"
}

# ── Funções de dados ─────────────────────────────────────
@st.cache_data(ttl=600)
def carregar_dados():
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = client.table("view_gd_resultados_dashboard").select("*").execute()
    df = pd.DataFrame(response.data)
    return df

def tratar_dados(df):
    df["resultado_data_plantio_dt"]  = pd.to_datetime(df["resultado_data_plantio"],  errors="coerce")
    df["resultado_data_colheita_dt"] = pd.to_datetime(df["resultado_data_colheita"], errors="coerce")

    df["plantio_fmt"]  = df["resultado_data_plantio_dt"].dt.strftime("%d/%m/%Y")
    df["colheita_fmt"] = df["resultado_data_colheita_dt"].dt.strftime("%d/%m/%Y")

    metricas = [
        "resultado_prod_scha",
        "resultado_prod_scha_corrigido",
        "resultado_area_ha",
        "resultado_umidade_colheita",
        "resultado_peso_mil_graos",
        "resultado_porcentagem_avariados"
    ]
    for col in metricas:
        df[col] = df[col].replace(0, pd.NA)

    def _status_ensaio(row):
        plantio  = pd.notna(row["resultado_data_plantio"])
        colheita = pd.notna(row["resultado_data_colheita"])
        prod     = pd.notna(row["resultado_prod_scha_corrigido"]) and row["resultado_prod_scha_corrigido"] > 0

        if plantio and colheita and prod:
            return "Com Resultado"
        elif (plantio and colheita and not prod) or (plantio and not colheita and not prod):
            return "Aguardando Colheita"
        else:
            return "Não Definido"

    df["status_ensaio"] = df.apply(_status_ensaio, axis=1)

    df["categoria_material"] = df["tratamentos_is_stine"].map({
        1.0: "STINE",
        0.0: "Concorrência"
    }).fillna("Concorrência")

    _pct = df.groupby(["fazenda_produtor", "cultura_nome"]).apply(
        lambda x: (x["tratamentos_is_stine"] == 1.0).sum() / len(x)
    ).reset_index(name="pct_stine")

    def _classificar(pct):
        if pct == 1.0:
            return "100% STINE"
        elif pct > 0.7:
            return "Maioria STINE (>70%)"
        elif pct >= 0.3:
            return "Misto (30-70%)"
        elif pct > 0:
            return "Maioria Conc (<30%)"
        else:
            return "100% Concorrência"

    _pct["classificacao_produtor"] = _pct["pct_stine"].apply(_classificar)

    df = df.merge(
        _pct[["fazenda_produtor", "cultura_nome", "classificacao_produtor"]],
        on=["fazenda_produtor", "cultura_nome"],
        how="left"
    )

    bins   = [0, 50, 200, 500, 2500, float("inf")]
    labels = ["Até 50 ha", "50 a 200 ha", "200 a 500 ha", "500 a 2.500 ha", "Acima de 2.500 ha"]

    df["faixa_area_milho"] = pd.cut(
        df["fazenda_area_plantada_milho"],
        bins=bins, labels=labels, right=True, include_lowest=True
    )

    df["faixa_area_soja"] = pd.cut(
        df["fazenda_area_plantada_soja"],
        bins=bins, labels=labels, right=True, include_lowest=True
    )

    def _ano_safra(dt):
        if pd.isna(dt):
            return "Sem data"
        mes   = dt.month
        ano   = dt.year
        safra = ano if mes >= 7 else ano - 1
        return f"{safra}/{str(safra + 1)[-2:]}"

    df["ano_safra"] = df["resultado_data_plantio_dt"].apply(_ano_safra)

    df["safra_completa"] = df.apply(
        lambda row: "Sem data" if row["ano_safra"] == "Sem data"
        else row["resultado_epoca"] + " " + row["ano_safra"],
        axis=1
    )

    return df

# ── Função card KPI ──────────────────────────────────────
def card(titulo, valor_principal, subtitulo, cor_borda):
    return f"""
        <div style="
            background-color: #FFFFFF;
            border-left: 4px solid {cor_borda};
            border-radius: 6px;
            padding: 16px 18px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            text-align: center;
        ">
            <p style="margin:0 0 6px 0; font-size:15px; color:#666; font-weight:500; text-align:left;">{titulo}</p>
            <p style="margin:0 0 6px 0; font-size:36px; font-weight:800; color:#1a1a1a; line-height:1.1;">{valor_principal}</p>
            <p style="margin:0; font-size:13px; color:#999; line-height:1.5;">{subtitulo}</p>
        </div>
    """

# ── Função section header ────────────────────────────────
def section_header(titulo):
    return f"""
        <div style="
            background-color: #EEEEEE;
            color: #444444;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
            padding: 8px 24px;
            margin: 24px 0 8px 0;
            border-radius: 4px;
        ">{titulo}</div>
    """

# ── Visão Hierárquica Regional → Cidade → RC → Produtor ─
def render_visao_hierarquica_regional(df):
    import html as _html
    total_geral = len(df)
    if total_geral == 0:
        return

    CORES = [
        "#166534", "#1d4ed8", "#7c2d12", "#6b21a8",
        "#0f766e", "#be185d", "#92400e", "#1e3a5f"
    ]

    def _semaforo(pct_resultado):
        """🟢 ≥ 60% | 🟡 30–59% | 🔴 < 30%"""
        if pct_resultado >= 60:
            return "🟢", "#dcfce7", "#166534"
        elif pct_resultado >= 30:
            return "🟡", "#fef9c3", "#854d0e"
        else:
            return "🔴", "#fee2e2", "#991b1b"

    def _cultura_badge(df_cid):
        cnt = df_cid["cultura_nome"].value_counts()
        if len(cnt) == 0:
            return ""
        dom = cnt.index[0]
        cor_c = "#005FAE" if dom == "Milho" else "#009D57"
        emoji = "🌽" if dom == "Milho" else "🌱"
        return (
            f'<span style="background:{cor_c}22; color:{cor_c}; font-size:11px;'
            f' font-weight:700; padding:2px 7px; border-radius:10px; white-space:nowrap;">'
            f'{emoji} {dom}</span>'
        )

    # CSS expander
    st.markdown("""
        <style>
        div[data-testid="stExpander"] > details {
            border: 1px solid #e5e7eb !important;
            border-radius: 8px !important;
            margin-bottom: 6px !important;
            background: #fff !important;
        }
        div[data-testid="stExpander"] > details > summary {
            padding: 10px 16px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
        }
        div[data-testid="stExpander"] > details > summary:hover {
            background: #f9fafb !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Cabeçalho
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <span style="font-size:16px;">🗺️</span>
            <span style="font-size:13px; color:#888;">Clique em uma regional para expandir</span>
            <span style="margin-left:auto; background:#1a1a1a; color:#fff;
                         font-size:12px; font-weight:700; padding:3px 12px; border-radius:20px;">
                {total_geral} ensaios no total
            </span>
        </div>
        <div style="background:#f8fafc; border:1px solid #e9ecef; border-radius:8px;
                    padding:10px 14px; margin-bottom:14px; font-size:12px; color:#555; line-height:2;">
            <strong style="color:#333;">O que aparece ao expandir por cidade:</strong>
            &nbsp; 🟢🟡🔴 <strong>Saúde</strong> (% com resultado) &nbsp;·&nbsp;
            📍 <strong>Cidade</strong> &nbsp;·&nbsp;
            🌱🌽 <strong>Cultura dominante</strong> &nbsp;·&nbsp;
            👥 <strong>Produtores únicos</strong> &nbsp;·&nbsp;
            📊 <strong>Status</strong> (resultado / aguardando) &nbsp;·&nbsp;
            % <strong>STINE</strong> &nbsp;·&nbsp;
            👤 <strong>RC principal</strong> &nbsp;·&nbsp;
            👤 <strong>Produtor principal</strong>
            <br>
            <span style="color:#555;">
                Semáforo: <span style="color:#166534; font-weight:700;">🟢 ≥ 60%</span> com resultado &nbsp;·&nbsp;
                <span style="color:#854d0e; font-weight:700;">🟡 30–59%</span> &nbsp;·&nbsp;
                <span style="color:#991b1b; font-weight:700;">🔴 &lt; 30%</span> &nbsp;·&nbsp;
                O <span style="background:#f0f4ff; color:#3b5bdb; font-weight:700;
                    padding:1px 6px; border-radius:10px;">+</span>
                no RC indica mais de um RC na cidade.
            </span>
        </div>
    """, unsafe_allow_html=True)

    # Monta regionais
    regionais = []
    for reg_nome, df_reg in df.groupby("regional_nome", sort=False):
        qtd_reg = len(df_reg)
        pct_reg = round(qtd_reg / total_geral * 100, 1)
        regionais.append((reg_nome, df_reg, qtd_reg, pct_reg))
    regionais.sort(key=lambda x: x[2], reverse=True)

    for idx, (reg_nome, df_reg, qtd_reg, pct_reg) in enumerate(regionais):
        cor = CORES[idx % len(CORES)]

        # KPIs resumidos da regional para o label do expander
        com_res_reg  = (df_reg["status_ensaio"] == "Com Resultado").sum()
        pct_res_reg  = round(com_res_reg / qtd_reg * 100, 1) if qtd_reg > 0 else 0
        icon_reg, _, _ = _semaforo(pct_res_reg)
        pct_stine_reg = round((df_reg["categoria_material"] == "STINE").sum() / qtd_reg * 100, 1) if qtd_reg > 0 else 0

        with st.expander(
            f"{icon_reg} {reg_nome}   —   {qtd_reg} ensaios ({pct_reg}%)   ·   "
            f"{pct_res_reg}% resultado   ·   {pct_stine_reg}% STINE",
            expanded=False
        ):
            reg_nome_esc = _html.escape(str(reg_nome))
            # Header interno da regional
            st.markdown(f"""
                <div style="display:flex; align-items:center; gap:10px; margin:-8px 0 12px 0;
                            padding-bottom:10px; border-bottom:1px solid #f0f0f0; flex-wrap:wrap;">
                    <span style="width:12px; height:12px; border-radius:50%;
                                 background:{cor}; flex-shrink:0; display:inline-block;"></span>
                    <span style="font-size:15px; font-weight:700; color:#1a1a1a;">{reg_nome_esc}</span>
                    <div style="flex:1; background:#e9ecef; border-radius:4px; height:8px;
                                overflow:hidden; min-width:60px;">
                        <div style="width:{pct_reg}%; height:100%; background:{cor}; border-radius:4px;"></div>
                    </div>
                    <span style="font-size:12px; font-weight:700; color:#444; white-space:nowrap;">
                        {qtd_reg} ensaios &nbsp;·&nbsp; {pct_reg}% do total &nbsp;·&nbsp;
                        {pct_res_reg}% com resultado &nbsp;·&nbsp; {pct_stine_reg}% STINE
                    </span>
                </div>
            """, unsafe_allow_html=True)

            # Top 10 cidades
            cidades_cnt = df_reg.groupby("cidade_nome").size().sort_values(ascending=False)
            top10 = cidades_cnt.head(10)
            outras_cnt = int(cidades_cnt.iloc[10:].sum()) if len(cidades_cnt) > 10 else 0

            for cidade_nome, qtd_cid in top10.items():
                df_cid = df_reg[df_reg["cidade_nome"] == cidade_nome]

                com_res  = int((df_cid["status_ensaio"] == "Com Resultado").sum())
                aguard   = int((df_cid["status_ensaio"] == "Aguardando Colheita").sum())
                pct_res  = round(com_res / qtd_cid * 100, 1) if qtd_cid > 0 else 0
                icon, bg_sem, cor_sem = _semaforo(pct_res)

                cult_badge = _cultura_badge(df_cid)
                n_prod    = int(df_cid["fazenda_produtor_uuid"].nunique())
                pct_stine = round((df_cid["categoria_material"] == "STINE").sum() / qtd_cid * 100, 1)
                cor_stine = "#166534" if pct_stine >= 60 else ("#854d0e" if pct_stine >= 30 else "#991b1b")

                rc_dom   = df_cid["usuario_nome"].value_counts()
                rc_raw   = rc_dom.index[0] if len(rc_dom) > 0 else ""
                rc_str   = _html.escape(str(rc_raw))
                varios    = len(rc_dom) > 1
                varios_tag = " +" if varios else ""

                df_rc    = df_cid[df_cid["usuario_nome"] == rc_raw]
                prod_dom  = df_rc["fazenda_produtor"].value_counts()
                prod_raw  = str(prod_dom.index[0]) if len(prod_dom) > 0 else ""
                prod_n    = int(prod_dom.iloc[0]) if len(prod_dom) > 0 else 0
                prod_esc  = _html.escape(prod_raw)
                prod_curto = _html.escape((prod_raw[:22] + "…") if len(prod_raw) > 22 else prod_raw)
                cidade_esc = _html.escape(str(cidade_nome))
                prod_html = f'👤 {prod_curto} ({prod_n})' if prod_raw else ""

                cols = st.columns([0.25, 1.6, 0.7, 0.85, 0.9, 0.85, 1.3, 1.5])
                with cols[0]:
                    st.markdown(f'<div style="padding:5px 0;font-size:17px;text-align:center;">{icon}</div>', unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f'<div style="padding:5px 0;font-weight:700;font-size:13px;color:#111;">📍 {cidade_esc}</div>', unsafe_allow_html=True)
                with cols[2]:
                    st.markdown(f'<div style="padding:5px 0;">{cult_badge}</div>', unsafe_allow_html=True)
                with cols[3]:
                    st.markdown(f'<div style="padding:5px 0;font-size:12px;color:#222;">👥 <b>{n_prod}</b> prod.</div>', unsafe_allow_html=True)
                with cols[4]:
                    st.markdown(f'<div style="padding:5px 0;font-size:12px;color:#222;">✅ <b>{com_res}</b> &nbsp;⏳ <b>{aguard}</b> <span style="color:#555;font-size:13px;font-weight:600;">/{qtd_cid}</span></div>', unsafe_allow_html=True)
                with cols[5]:
                    st.markdown(f'<div style="padding:5px 0;font-size:12px;font-weight:700;color:{cor_stine};">{pct_stine}% STINE</div>', unsafe_allow_html=True)
                with cols[6]:
                    st.markdown(f'<div style="padding:5px 0;"><span style="background:#f0f4ff;color:#3b5bdb;font-size:11px;font-weight:600;padding:2px 7px;border-radius:10px;">👤 {rc_str}{varios_tag}</span></div>', unsafe_allow_html=True)
                with cols[7]:
                    st.markdown(f'<div style="padding:5px 0;font-size:12px;color:#333;" title="{prod_esc}">{prod_html}</div>', unsafe_allow_html=True)

            if outras_cnt > 0:
                n_outras = len(cidades_cnt) - 10
                st.markdown(f'<div style="font-size:12px;color:#aaa;padding:4px 0;font-style:italic;">+ outras {n_outras} cidades → {outras_cnt} ensaios</div>', unsafe_allow_html=True)


# ── CSS global ───────────────────────────────────────────
st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
        }
        div.stButton > button {
            background-color: #555555;
            color: white;
            border: none;
            margin-left: 0px;
            white-space: nowrap;
        }
        div.stButton > button:hover {
            background-color: #333333;
            color: white;
            border: none;
        }
        /* Aba ativa */
        button[kind="primary"] {
            background-color: #444444 !important;
            color: white !important;
            border-radius: 0px !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            height: 44px !important;
        }
        button[kind="primary"]:hover {
            background-color: #333333 !important;
        }
        /* Aba inativa */
        button[kind="secondary"] {
            background-color: #e0e0e0 !important;
            color: #777777 !important;
            border-radius: 0px !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 14px !important;
            font-weight: 400 !important;
            height: 44px !important;
        }
        button[kind="secondary"]:hover {
            background-color: #cccccc !important;
            color: #333333 !important;
        }    </style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────
safra_label = st.session_state.get("sel_safra", "Todos")
safra_texto = safra_label if safra_label != "Todos" else "Todas as Safras"

st.markdown(f"""
    <div style="
        background-color: transparent;
        padding: 28px 0px 16px 0px;
        width: 100%;
        border-bottom: 1px solid #dee2e6;
    ">
        <h1 style="
            color: #1a1a1a;
            font-size: 28px;
            font-weight: 700;
            margin: 0 0 6px 0;
            letter-spacing: 0.3px;
        ">Dashboard de Acompanhamento das Áreas de Geração de Demanda (GD)</h1>
        <p style="
            color: #888;
            font-size: 13px;
            margin: 0;
            font-weight: 400;
        ">Áreas Soja e Milho &nbsp;|&nbsp; Safra: <strong style="color:#555">{safra_texto}</strong></p>
    </div>
""", unsafe_allow_html=True)

# ── Abas de navegação ────────────────────────────────────
pagina_ativa = st.session_state["pagina"]

col_aba1, col_aba2 = st.columns(2)

with col_aba1:
    if st.button(
        "📊 Gestão de Áreas",
        use_container_width=True,
        type="primary" if pagina_ativa == "areas" else "secondary"
    ):
        st.session_state["pagina"] = "areas"
        st.rerun()

with col_aba2:
    if st.button(
        "🎯 Performance de Materiais",
        use_container_width=True,
        type="primary" if pagina_ativa == "performance" else "secondary"
    ):
        st.session_state["pagina"] = "performance"
        st.rerun()

st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

# ── Carrega e trata dados ────────────────────────────────
with st.spinner("Buscando dados atualizados..."):
    df = carregar_dados()
    df = tratar_dados(df)

# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    # CSS botões da sidebar quadrados
    st.markdown("""
        <style>
        [data-testid="stSidebar"] div.stButton > button {
            border-radius: 4px !important;
            --border-radius: 4px !important;
            background-color: #f8f9fa !important;
            color: #555 !important;
            border: 1px solid #cccccc !important;
            font-size: 12px !important;
            padding: 0 12px !important;
            margin-left: 0 !important;
            font-weight: 400 !important;
        }
        [data-testid="stSidebar"] div.stButton > button:hover {
            background-color: #e9ecef !important;
            border-color: #666 !important;
            color: #222 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Botão atualizar no topo, antes do título Filtros
    _, col_mid, _ = st.columns([0.5, 3, 0.5])
    with col_mid:
        if st.button("🔄 Atualizar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown("""
        <div style="
            padding: 16px 0 8px 0;
            border-bottom: 2px solid #aaaaaa;
            margin-bottom: 12px;
            margin-top: 8px;
        ">
            <p style="
                margin: 0;
                font-size: 16px;
                font-weight: 700;
                color: #231F20;
                letter-spacing: 0.5px;
            ">Filtros</p>
        </div>
    """, unsafe_allow_html=True)

    _, col_mid2, _ = st.columns([0.5, 3, 0.5])
    with col_mid2:
        if st.button("✕ Limpar filtros", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key.startswith(("reg_", "est_", "cid_", "sts_", "cat_", "usr_", "tim_")):
                    st.session_state[key] = False
            st.session_state["sel_cultura"] = "Todos"
            st.session_state["sel_safra"]   = "Todos"
            st.rerun()
    culturas = ["Todos"] + sorted(df["cultura_nome"].unique().tolist())
    sel_cultura = st.selectbox(
        "Cultura",
        options=culturas,
        key="sel_cultura"
    )

    # Safra em cascata com cultura
    df_temp = df.copy()
    if sel_cultura != "Todos":
        df_temp = df_temp[df_temp["cultura_nome"] == sel_cultura]

    safras = ["Todos"] + sorted(df_temp["safra_completa"].unique().tolist())
    sel_safra = st.selectbox(
        "Safra",
        options=safras,
        key="sel_safra"
    )

    if sel_safra != "Todos":
        df_temp = df_temp[df_temp["safra_completa"] == sel_safra]

    # Regional
    with st.expander("Regional"):
        regionais = sorted(df_temp["regional_nome"].unique().tolist())
        sel_regional = [r for r in regionais if st.checkbox(r, value=False, key=f"reg_{r}")]

    df_temp2 = df_temp[df_temp["regional_nome"].isin(sel_regional)] if sel_regional else df_temp

    # Estado
    with st.expander("Estado"):
        estados = sorted(df_temp2["estado_nome"].unique().tolist())
        sel_estado = [e for e in estados if st.checkbox(e, value=False, key=f"est_{e}")]

    df_temp3 = df_temp2[df_temp2["estado_nome"].isin(sel_estado)] if sel_estado else df_temp2

    # Cidade
    with st.expander("Cidade"):
        cidades = sorted(df_temp3["cidade_nome"].unique().tolist())
        sel_cidade = [c for c in cidades if st.checkbox(c, value=False, key=f"cid_{c}")]

    df_temp4 = df_temp3[df_temp3["cidade_nome"].isin(sel_cidade)] if sel_cidade else df_temp3

    # Status Ensaio
    with st.expander("Status Ensaio"):
        status = sorted(df_temp4["status_ensaio"].unique().tolist())
        sel_status = [s for s in status if st.checkbox(s, value=False, key=f"sts_{s}")]

    # Usuário
    with st.expander("Usuário"):
        usuarios = sorted(df_temp4["usuario_nome"].unique().tolist())
        sel_usuario = [u for u in usuarios if st.checkbox(u, value=False, key=f"usr_{u}")]

    df_temp5 = df_temp4[df_temp4["usuario_nome"].isin(sel_usuario)] if sel_usuario else df_temp4

    # Time
    with st.expander("Time"):
        times = sorted(df_temp5["usuario_time"].unique().tolist())
        sel_time = [t for t in times if st.checkbox(t, value=False, key=f"tim_{t}")]

# ── Aplica filtros ───────────────────────────────────────
df_filtrado = df.copy()

if sel_cultura != "Todos":
    df_filtrado = df_filtrado[df_filtrado["cultura_nome"] == sel_cultura]

if sel_safra != "Todos":
    df_filtrado = df_filtrado[df_filtrado["safra_completa"] == sel_safra]

df_filtrado = df_filtrado[
    (df_filtrado["regional_nome"].isin(sel_regional) if sel_regional else pd.Series(True, index=df_filtrado.index)) &
    (df_filtrado["estado_nome"].isin(sel_estado) if sel_estado else pd.Series(True, index=df_filtrado.index)) &
    (df_filtrado["cidade_nome"].isin(sel_cidade) if sel_cidade else pd.Series(True, index=df_filtrado.index)) &
    (df_filtrado["status_ensaio"].isin(sel_status) if sel_status else pd.Series(True, index=df_filtrado.index)) &
    (df_filtrado["usuario_nome"].isin(sel_usuario) if sel_usuario else pd.Series(True, index=df_filtrado.index)) &
    (df_filtrado["usuario_time"].isin(sel_time) if sel_time else pd.Series(True, index=df_filtrado.index))
]

# ── Filtro ativo ─────────────────────────────────────────
filtro_ativo = len(sel_regional) > 0

# ═══════════════════════════════════════════════════════════
# PÁGINA: GESTÃO DE ÁREAS
# ═══════════════════════════════════════════════════════════
if st.session_state["pagina"] == "areas":

     # ── KPIs ─────────────────────────────────────────────────
    total_areas    = df_filtrado["resultado_uuid"].nunique()
    total_clientes = df_filtrado["fazenda_produtor_uuid"].nunique()
    com_resultado  = df_filtrado[df_filtrado["status_ensaio"] == "Com Resultado"].shape[0]
    aguardando     = df_filtrado[df_filtrado["status_ensaio"] == "Aguardando Colheita"].shape[0]

    pct_resultado  = round(com_resultado / total_areas * 100, 1) if total_areas > 0 else 0
    pct_aguardando = round(aguardando    / total_areas * 100, 1) if total_areas > 0 else 0
    nao_definido   = df_filtrado[df_filtrado["status_ensaio"] == "Não Definido"].shape[0]
    pct_nao_def    = round(nao_definido / total_areas * 100, 1) if total_areas > 0 else 0

    # Potencial de área — soma por produtor único para evitar duplicidade
    produtores_unicos = df_filtrado.drop_duplicates(subset="fazenda_produtor_uuid")
    cobertura_gd   = round(total_areas / total_clientes, 1) if total_clientes > 0 else 0
    pot_soja   = int(produtores_unicos["fazenda_area_plantada_soja"].fillna(0).sum())
    pot_milho  = int(produtores_unicos["fazenda_area_plantada_milho"].fillna(0).sum())
    n_prod     = len(produtores_unicos)
    media_soja  = round(pot_soja  / n_prod, 1) if n_prod > 0 else 0
    media_milho = round(pot_milho / n_prod, 1) if n_prod > 0 else 0


    # Título infográfico acima dos cards
    st.markdown("""
        <div style="padding: 24px 0px 0px 0px;">
            <div style="
                background: white;
                border-radius: 6px;
                padding: 16px 20px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.06);
                margin-bottom: 24px;
                border-left: 4px solid #333;
            ">
                <p style="margin:0 0 6px 0; font-size:15px; font-weight:700; color:#1a1a1a;">O que é considerado uma Área?</p>
                <p style="margin:0; font-size:13px; color:#555; line-height:1.6;">
                    Cada <strong>Área</strong> representa um ensaio de geração de demanda onde um cultivar/híbrido é plantado em uma faixa específica da propriedade do produtor. Após a colheita, essa área é avaliada para medir a performance do material em condições reais de cultivo.
                </p>
            </div>
        </div>
        <div style="padding: 0px 0px 16px 0px;">
            <p style="
                margin: 0 0 6px 0;
                font-size: 11px;
                font-weight: 700;
                color: #1a1a1a;
                letter-spacing: 2px;
                text-transform: uppercase;
            ">Panorama das Áreas</p>
            <div style="margin:0 0 8px 0; font-size:32px; font-weight:800; color:#1a1a1a; line-height:1.2;">Como está nossa base hoje</div>
            <p style="
                margin: 0;
                font-size: 14px;
                color: #666;
                line-height: 1.6;
                max-width: 860px;
            ">Antes de mergulhar nos detalhes, um retrato atual da quantidade de áreas, do estágio em que se encontram e do potencial de cultivo para soja e milho na carteira de clientes.</p>
        </div>
    """, unsafe_allow_html=True)

    col0, col1, colg1, col2, colg2, col3, colg3, col4, colg4, col5, colg5, col6, col_end = st.columns([0.5, 3, 0.3, 3, 0.3, 3, 0.3, 3, 0.3, 3, 0.3, 3, 0.5])

    # Formata números grandes de forma legível
    def fmt_ha(valor):
        if valor >= 1_000_000:
            return f"{valor/1_000_000:.2f}M ha".replace(".", ",")
        elif valor >= 1_000:
            return f"{valor/1_000:.1f}K ha".replace(".", ",")
        return f"{valor:,} ha".replace(",", ".")

    with col1:
        st.markdown(card(
            "Visão geral das áreas",
            f"{total_areas:,}".replace(",", "."),
            f"{total_clientes:,} produtores ativos".replace(",", "."),
            "#005FAE"
        ), unsafe_allow_html=True)

    with col2:
        st.markdown(card(
            "Áreas já avaliadas",
            f"{com_resultado:,}".replace(",", "."),
            f"{pct_resultado}% do total",
            "#7ED321"
        ), unsafe_allow_html=True)

    with col3:
        st.markdown(card(
            "Áreas ainda em campo",
            f"{aguardando:,}".replace(",", "."),
            f"{pct_aguardando}% do total",
            "#D97706"
        ), unsafe_allow_html=True)

    with col4:
        st.markdown(card(
            "Potencial de soja na base",
            fmt_ha(pot_soja),
            f"média {str(media_soja).replace('.', ',')} ha/produtor",
            "#009D57"
        ), unsafe_allow_html=True)

    with col5:
        st.markdown(card(
            "Potencial de milho na base",
            fmt_ha(pot_milho),
            f"média {str(media_milho).replace('.', ',')} ha/produtor",
            "#005FAE"
        ), unsafe_allow_html=True)

    with col6:
        st.markdown(card(
            "Cobertura de GD na base",
            f"{str(cobertura_gd).replace('.', ',')}",
            "áreas por produtor ativo",
            "#7C3AED"
        ), unsafe_allow_html=True)


    st.markdown("""
        <div style="margin: 24px 0 4px 0;">
            <p style="margin:0 0 4px 0; font-size:11px; font-weight:700; color:#1a1a1a; letter-spacing:2px; text-transform:uppercase;">Visão Geral</p>
            <div style="margin:0 0 8px 0; font-size:26px; font-weight:800; color:#1a1a1a; line-height:1.2;">Como as áreas estão distribuídas</div>
            <p style="margin:0; font-size:14px; color:#666; line-height:1.6; max-width:860px;">Distribuição das áreas por status de avaliação e por cultura. Use esses gráficos para entender o estágio atual da base e o mix entre soja e milho.</p>
        </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        status_count = df_filtrado["status_ensaio"].value_counts().reset_index()
        status_count.columns = ["status", "qtd"]
        total = status_count["qtd"].sum()

        status_count["legenda"] = status_count.apply(
            lambda r: f"{r['status']} ({round(r['qtd']/total*100,1)}%)", axis=1
        )

        fig_status = px.pie(
            status_count, values="qtd", names="legenda",
            hole=0.6, title="Status das Áreas",
            color="status", color_discrete_map=cores_status
        )
        fig_status.update_traces(
            textinfo="value",
            textfont=dict(color="black", size=13),
            textposition="outside",
            domain=dict(x=[0.1, 0.75])
        )
        fig_status.update_layout(
            height=300,
            title_font_size=14,
            title_x=0,
            title_xanchor="left",
            margin=dict(l=40, r=160, t=50, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="v", x=0.82, y=0.5, font=dict(color="black", size=12)),
            annotations=[dict(text=str(total), x=0.42, y=0.5, font_size=30, showarrow=False, font_color="black")]
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with col2:
        cultura_count = df_filtrado["cultura_nome"].value_counts().reset_index()
        cultura_count.columns = ["cultura", "qtd"]
        total_cult = cultura_count["qtd"].sum()

        cultura_count["legenda"] = cultura_count.apply(
            lambda r: f"{r['cultura']} ({round(r['qtd']/total_cult*100,1)}%)", axis=1
        )

        fig_cultura = px.pie(
            cultura_count, values="qtd", names="legenda",
            hole=0.6, title="Mix de Culturas",
            color="cultura", color_discrete_map=cores_cultura
        )
        fig_cultura.update_traces(
            textinfo="value",
            textfont=dict(color="black", size=13),
            textposition="outside",
            domain=dict(x=[0.1, 0.75])
        )
        fig_cultura.update_layout(
            height=300,
            title_font_size=14,
            title_x=0,
            title_xanchor="left",
            margin=dict(l=40, r=160, t=50, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="v", x=0.82, y=0.5, font=dict(color="black", size=12)),
            annotations=[dict(text=str(total_cult), x=0.42, y=0.5, font_size=30, showarrow=False, font_color="black")]
        )
        st.plotly_chart(fig_cultura, use_container_width=True)

    # ── Indicadores de saúde ─────────────────────────────────
    cor_resultado = "#0891B2" if pct_resultado >= 90 else ("#D97706" if pct_resultado >= 60 else "#DC2626")
    cor_nao_def   = "#DC2626" if pct_nao_def >= 10 else ("#D97706" if pct_nao_def >= 5 else "#0891B2")
    icon_resultado = "✅" if pct_resultado >= 90 else ("⚠️" if pct_resultado >= 60 else "🔴")
    icon_nao_def   = "🔴" if pct_nao_def >= 10 else ("⚠️" if pct_nao_def >= 5 else "✅")

    st.markdown(f"""
        <div style="display:flex; gap:16px; margin: 16px 0 24px 0;">
            <div style="flex:1; background:white; border-radius:8px; padding:16px 20px;
                        box-shadow:0 2px 6px rgba(0,0,0,0.06); border-left:4px solid {cor_resultado};">
                <p style="margin:0 0 4px 0; font-size:11px; font-weight:700; color:#888; letter-spacing:1px; text-transform:uppercase;">
                    {icon_resultado} Saúde — Fechamento de Resultado
                </p>
                <p style="margin:0; font-size:28px; font-weight:800; color:{cor_resultado};">{pct_resultado}%</p>
                <p style="margin:4px 0 0 0; font-size:12px; color:#666;">das áreas já têm resultado registrado ({com_resultado} de {total_areas})</p>
                <p style="margin:12px 0 0 0; font-size:11px; color:#aaa; border-top:1px solid #f0f0f0; padding-top:8px;">
                    <span style="color:#0891B2;">●</span> ≥ 90% bom &nbsp;
                    <span style="color:#D97706;">●</span> 60–89% atenção &nbsp;
                    <span style="color:#DC2626;">●</span> &lt; 60% crítico
                </p>
            </div>
            <div style="flex:1; background:white; border-radius:8px; padding:16px 20px;
                        box-shadow:0 2px 6px rgba(0,0,0,0.06); border-left:4px solid {cor_nao_def};">
                <p style="margin:0 0 4px 0; font-size:11px; font-weight:700; color:#888; letter-spacing:1px; text-transform:uppercase;">
                    {icon_nao_def} Ponto de Atenção — Sem Status Definido
                </p>
                <p style="margin:0; font-size:28px; font-weight:800; color:{cor_nao_def};">{pct_nao_def}%</p>
                <p style="margin:4px 0 0 0; font-size:12px; color:#666;">das áreas estão sem status definido ({nao_definido} de {total_areas})</p>
                <p style="margin:12px 0 0 0; font-size:11px; color:#aaa; border-top:1px solid #f0f0f0; padding-top:8px;">
                    <span style="color:#0891B2;">●</span> &lt; 5% bom &nbsp;
                    <span style="color:#D97706;">●</span> 5–9% atenção &nbsp;
                    <span style="color:#DC2626;">●</span> ≥ 10% crítico
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Linha 3 — Barras por Regional e Estado
    st.markdown("""
        <div style="margin: 24px 0 20px 0;">
            <p style="margin: 0 0 6px 0; font-size: 11px; font-weight: 700; color: #1a1a1a; letter-spacing: 2px; text-transform: uppercase;">Distribuição por Regional e Estado</p>
            <h2 style="margin: 0 0 8px 0; font-size: 26px; font-weight: 800; color: #1a1a1a; line-height: 1.2;">Onde estão nossas áreas</h2>
            <p style="margin: 0; font-size: 14px; color: #666; line-height: 1.6; max-width: 860px;">Distribuição das áreas por regional comercial e por estado. Identifique as regiões com maior concentração e aquelas com maior potencial de expansão.</p>
        </div>
    """, unsafe_allow_html=True)
    col3, col4 = st.columns(2)

    with col3:
        reg = df_filtrado.groupby(["regional_nome", "status_ensaio"]).size().reset_index(name="qtd")
        reg["rotulo"] = reg["qtd"].apply(lambda x: str(x) if x >= 20 else "")
        fig_reg = px.bar(
            reg, x="qtd", y="regional_nome", color="status_ensaio",
            orientation="h", title="Áreas por Regional",
            color_discrete_map=cores_status, text="rotulo"
        )
        fig_reg.update_traces(textfont=dict(color="black", size=12))
        fig_reg.update_layout(
            height=450, title_font_size=14, title_x=0, title_xanchor="left",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=40, t=50, b=80),
            legend_title="Status", yaxis_title="", xaxis_title="Áreas",
            yaxis=dict(tickfont=dict(color="black")),
            xaxis=dict(tickfont=dict(color="black")),
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, font=dict(color="black"))
        )
        st.plotly_chart(fig_reg, use_container_width=True)

    with col4:
        est = df_filtrado.groupby(["estado_nome", "status_ensaio"]).size().reset_index(name="qtd")
        est["rotulo"] = est["qtd"].apply(lambda x: str(x) if x >= 20 else "")
        fig_est = px.bar(
            est, x="qtd", y="estado_nome", color="status_ensaio",
            orientation="h", title="Áreas por Estado",
            color_discrete_map=cores_status, text="rotulo"
        )
        fig_est.update_traces(textfont=dict(color="black", size=12))
        fig_est.update_layout(
            height=450, title_font_size=14, title_x=0, title_xanchor="left",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=40, t=50, b=80),
            legend_title="Status", yaxis_title="", xaxis_title="Áreas",
            yaxis=dict(tickfont=dict(color="black")),
            xaxis=dict(tickfont=dict(color="black")),
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, font=dict(color="black"))
        )
        st.plotly_chart(fig_est, use_container_width=True)

    # ── Tabelas resumo ────────────────────────────────────────
    pct_renderer = JsCode("""
        class ProgressRenderer {
            init(params) {
                this.eGui = document.createElement('div');
                this.eGui.style.cssText = 'position:relative; width:100%; height:100%; display:flex; align-items:center;';
                var pct = params.value || 0;
                var bar = document.createElement('div');
                bar.style.cssText = 'position:absolute; left:0; top:15%; height:70%; width:' + pct + '%; background:#009D57; opacity:0.25; border-radius:2px;';
                var label = document.createElement('span');
                label.style.cssText = 'position:relative; z-index:1; font-weight:600; font-size:12px; padding-left:6px;';
                label.innerText = pct.toFixed(1) + '%';
                this.eGui.appendChild(bar);
                this.eGui.appendChild(label);
            }
            getGui() { return this.eGui; }
        }
    """)

    tab_col1, tab_col2 = st.columns(2)

    with tab_col1:
        reg_tabela = df_filtrado.groupby("regional_nome").agg(
            Total=("resultado_uuid", "count"),
            Com_Resultado=("status_ensaio", lambda x: (x == "Com Resultado").sum()),
            Aguardando=("status_ensaio", lambda x: (x == "Aguardando Colheita").sum()),
            Nao_Definido=("status_ensaio", lambda x: (x == "Não Definido").sum()),
        ).reset_index()
        reg_tabela["% Resultado"] = (reg_tabela["Com_Resultado"] / reg_tabela["Total"] * 100).round(1)
        reg_tabela = reg_tabela.sort_values("Total", ascending=False)
        reg_tabela.columns = ["Regional", "Total", "Com Resultado", "Aguardando", "Não Definido", "% Resultado"]

        gb_reg = GridOptionsBuilder.from_dataframe(reg_tabela)
        gb_reg.configure_default_column(resizable=True, sortable=True, filter=True)
        gb_reg.configure_column("Com Resultado", headerClass="header-com-resultado")
        gb_reg.configure_column("Aguardando", headerClass="header-aguardando")
        gb_reg.configure_column("Não Definido", headerClass="header-nao-definido")
        gb_reg.configure_column("% Resultado", type=["numericColumn"], cellRenderer=pct_renderer)

        custom_css = {
            ".header-com-resultado": {"background-color": "rgba(126,211,33,0.25) !important", "color": "#4a7a00 !important", "font-weight": "700 !important"},
            ".header-aguardando": {"background-color": "rgba(74,144,217,0.25) !important", "color": "#1a4d8a !important", "font-weight": "700 !important"},
            ".header-nao-definido": {"background-color": "rgba(158,158,158,0.25) !important", "color": "#444 !important", "font-weight": "700 !important"},
        }

        AgGrid(reg_tabela, gridOptions=gb_reg.build(),
               fit_columns_on_grid_load=True, height=320,
               allow_unsafe_jscode=True, theme="alpine",
               custom_css=custom_css)

    with tab_col2:
        est_tabela = df_filtrado.groupby("estado_nome").agg(
            Total=("resultado_uuid", "count"),
            Com_Resultado=("status_ensaio", lambda x: (x == "Com Resultado").sum()),
            Aguardando=("status_ensaio", lambda x: (x == "Aguardando Colheita").sum()),
            Nao_Definido=("status_ensaio", lambda x: (x == "Não Definido").sum()),
        ).reset_index()
        est_tabela["% Resultado"] = (est_tabela["Com_Resultado"] / est_tabela["Total"] * 100).round(1)
        est_tabela = est_tabela.sort_values("Total", ascending=False)
        est_tabela.columns = ["Estado", "Total", "Com Resultado", "Aguardando", "Não Definido", "% Resultado"]

        gb_est = GridOptionsBuilder.from_dataframe(est_tabela)
        gb_est.configure_default_column(resizable=True, sortable=True, filter=True)
        gb_est.configure_column("Com Resultado", headerClass="header-com-resultado")
        gb_est.configure_column("Aguardando", headerClass="header-aguardando")
        gb_est.configure_column("Não Definido", headerClass="header-nao-definido")
        gb_est.configure_column("% Resultado", type=["numericColumn"], cellRenderer=pct_renderer)
        AgGrid(est_tabela, gridOptions=gb_est.build(),
               fit_columns_on_grid_load=True, height=320,
               allow_unsafe_jscode=True, theme="alpine",
               custom_css=custom_css)

    # Linha 4 — Áreas por RC
    if filtro_ativo:
        st.markdown("""
            <div style="margin: 24px 0 20px 0;">
                <p style="margin: 0 0 6px 0; font-size: 11px; font-weight: 700; color: #1a1a1a; letter-spacing: 2px; text-transform: uppercase;">Análise por RC</p>
                <h2 style="margin: 0 0 8px 0; font-size: 26px; font-weight: 800; color: #1a1a1a; line-height: 1.2;">Performance por representante</h2>
                <p style="margin: 0; font-size: 14px; color: #666; line-height: 1.6; max-width: 860px;">Visualize a distribuição de áreas e o mix de materiais por RC, identificando quais representantes possuem maior cobertura e diversificação de cultivares.</p>
            </div>
        """, unsafe_allow_html=True)

        rc = df_filtrado.groupby("usuario_nome").size().reset_index(name="qtd")
        rc = rc.sort_values("qtd", ascending=True)
        rc["rotulo"] = rc["qtd"].apply(lambda x: f"{x} áreas" if x >= 10 else "")

        fig_rc = px.bar(
            rc, x="qtd", y="usuario_nome",
            orientation="h", title="Áreas por RC",
            text="rotulo", color_discrete_sequence=["#4A90D9"]
        )
        fig_rc.update_traces(textfont=dict(color="black", size=12), textposition="outside")
        fig_rc.update_layout(
            height=max(400, len(rc) * 28),
            title_font_size=14,
            title_font_color="black",
            title_x=0,
            title_xanchor="left",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=120, t=50, b=40),
            yaxis_title="", xaxis_title="",
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(tickfont=dict(color="black", size=12), categoryorder="total ascending")
        )
        st.plotly_chart(fig_rc, use_container_width=True)

        # ── Soja vs Milho por RC ─────────────────────────────
        cult_rc = df_filtrado.groupby(["usuario_nome", "cultura_nome"]).size().reset_index(name="qtd")
        cult_rc["rotulo"] = cult_rc["qtd"].apply(lambda x: str(x) if x >= 10 else "")
        cult_order = cult_rc.groupby("usuario_nome")["qtd"].sum().sort_values(ascending=True).index.tolist()

        fig_cult_rc = px.bar(
            cult_rc, x="qtd", y="usuario_nome", color="cultura_nome",
            orientation="h", title="Soja vs Milho por RC",
            color_discrete_map=cores_cultura, text="rotulo", barmode="stack"
        )
        fig_cult_rc.update_traces(textfont=dict(color="white", size=11), textposition="inside")
        fig_cult_rc.update_layout(
            height=max(400, len(cult_order) * 28),
            title_font_size=14,
            title_font_color="black",
            title_x=0,
            title_xanchor="left",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=40, t=50, b=60),
            legend_title="", yaxis_title="", xaxis_title="",
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(
                tickfont=dict(color="black", size=12),
                categoryorder="array",
                categoryarray=cult_order
            ),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, font=dict(color="black"))
        )
        st.plotly_chart(fig_cult_rc, use_container_width=True)

        # ── Tabela Soja vs Milho por RC ─────────────────────
        cult_tabela = df_filtrado.groupby(["usuario_nome", "cultura_nome"]).size().reset_index(name="Qtd")
        cult_tabela = cult_tabela.pivot(index="usuario_nome", columns="cultura_nome", values="Qtd").fillna(0).astype(int)
        cult_tabela["Total"] = cult_tabela.sum(axis=1)
        cult_tabela["% Soja"] = (cult_tabela.get("Soja", 0) / cult_tabela["Total"] * 100).round(1)
        cult_tabela["% Milho"] = (cult_tabela.get("Milho", 0) / cult_tabela["Total"] * 100).round(1)
        cult_tabela = cult_tabela.sort_values("Total", ascending=False).reset_index()
        cult_tabela.columns.name = None
        cult_tabela = cult_tabela.rename(columns={"usuario_nome": "RC"})

        pct_soja_renderer = JsCode("""
            class ProgressSojaRenderer {
                init(params) {
                    this.eGui = document.createElement('div');
                    this.eGui.style.cssText = 'position:relative; width:100%; height:100%; display:flex; align-items:center;';
                    var pct = params.value || 0;
                    var bar = document.createElement('div');
                    bar.style.cssText = 'position:absolute; left:0; top:15%; height:70%; width:' + pct + '%; background:#009D57; opacity:0.25; border-radius:2px;';
                    var label = document.createElement('span');
                    label.style.cssText = 'position:relative; z-index:1; font-weight:600; font-size:12px; padding-left:6px;';
                    label.innerText = pct.toFixed(1) + '%';
                    this.eGui.appendChild(bar);
                    this.eGui.appendChild(label);
                }
                getGui() { return this.eGui; }
            }
        """)

        pct_milho_renderer = JsCode("""
            class ProgressMilhoRenderer {
                init(params) {
                    this.eGui = document.createElement('div');
                    this.eGui.style.cssText = 'position:relative; width:100%; height:100%; display:flex; align-items:center;';
                    var pct = params.value || 0;
                    var bar = document.createElement('div');
                    bar.style.cssText = 'position:absolute; left:0; top:15%; height:70%; width:' + pct + '%; background:#005FAE; opacity:0.25; border-radius:2px;';
                    var label = document.createElement('span');
                    label.style.cssText = 'position:relative; z-index:1; font-weight:600; font-size:12px; padding-left:6px;';
                    label.innerText = pct.toFixed(1) + '%';
                    this.eGui.appendChild(bar);
                    this.eGui.appendChild(label);
                }
                getGui() { return this.eGui; }
            }
        """)

        cult_css = {
            ".header-soja": {"background-color": "rgba(0,157,87,0.25) !important", "color": "#004d2a !important", "font-weight": "700 !important"},
            ".header-milho": {"background-color": "rgba(0,95,174,0.2) !important", "color": "#00336b !important", "font-weight": "700 !important"},
            ".header-pct-soja": {"background-color": "rgba(0,157,87,0.15) !important", "color": "#004d2a !important", "font-weight": "700 !important"},
            ".header-pct-milho": {"background-color": "rgba(0,95,174,0.12) !important", "color": "#00336b !important", "font-weight": "700 !important"},
        }

        gb_cult = GridOptionsBuilder.from_dataframe(cult_tabela)
        gb_cult.configure_default_column(resizable=True, sortable=True, filter=True)
        if "Soja" in cult_tabela.columns:
            gb_cult.configure_column("Soja", headerClass="header-soja")
        if "Milho" in cult_tabela.columns:
            gb_cult.configure_column("Milho", headerClass="header-milho")
        gb_cult.configure_column("% Soja", type=["numericColumn"], cellRenderer=pct_soja_renderer, headerClass="header-pct-soja")
        gb_cult.configure_column("% Milho", type=["numericColumn"], cellRenderer=pct_milho_renderer, headerClass="header-pct-milho")
        gb_cult.configure_column("% Milho", type=["numericColumn"], cellRenderer=pct_milho_renderer)
        AgGrid(cult_tabela, gridOptions=gb_cult.build(),
               fit_columns_on_grid_load=True, height=350,
               allow_unsafe_jscode=True, theme="alpine",
               custom_css=cult_css)
    else:
        st.markdown("""
            <div style='padding: 24px 0px; margin-top: 8px;'>
                <p style='color: #888; font-size: 13px; text-align: center;'>
                    📊 Selecione ao menos uma <b>Regional</b> no filtro para visualizar as áreas por RC.
                </p>
            </div>
        """, unsafe_allow_html=True)

    # Linha 5 — Mix de Materiais por RC
    if filtro_ativo:

        mix = df_filtrado.groupby(["usuario_nome", "categoria_material"]).size().reset_index(name="qtd")
        mix["rotulo"] = mix["qtd"].apply(lambda x: str(x) if x >= 15 else "")
        mix_order = mix.groupby("usuario_nome")["qtd"].sum().sort_values(ascending=True).index.tolist()

        fig_mix = px.bar(
            mix, x="qtd", y="usuario_nome", color="categoria_material",
            orientation="h", title="Mix de Materiais por RC",
            color_discrete_map=cores_mix, text="rotulo", barmode="stack"
        )
        fig_mix.update_traces(textfont=dict(color="white", size=11), textposition="inside")
        fig_mix.update_layout(
            height=max(400, len(mix_order) * 28),
            title_font_size=14,
            title_font_color="black",
            title_x=0,
            title_xanchor="left",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=40, t=50, b=60),
            legend_title="", yaxis_title="", xaxis_title="",
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(
                tickfont=dict(color="black", size=12),
                categoryorder="array",
                categoryarray=mix_order
            ),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, font=dict(color="black", size=12))
        )
        st.plotly_chart(fig_mix, use_container_width=True)

        # ── Tabela Mix de Materiais por RC ──────────────────
        mix_tabela = df_filtrado.groupby(["usuario_nome", "categoria_material"]).size().reset_index(name="Qtd")
        mix_tabela = mix_tabela.pivot(index="usuario_nome", columns="categoria_material", values="Qtd").fillna(0).astype(int)
        mix_tabela["Total"] = mix_tabela.sum(axis=1)
        mix_tabela["% STINE"] = (mix_tabela.get("STINE", 0) / mix_tabela["Total"] * 100).round(1)
        mix_tabela["% Concorrência"] = (mix_tabela.get("Concorrência", 0) / mix_tabela["Total"] * 100).round(1)
        mix_tabela = mix_tabela.sort_values("Total", ascending=False).reset_index()
        mix_tabela.columns.name = None
        mix_tabela = mix_tabela.rename(columns={"usuario_nome": "RC"})

        pct_stine_renderer = JsCode("""
            class PctStineRenderer {
                init(params) {
                    this.eGui = document.createElement('div');
                    this.eGui.style.cssText = 'position:relative; width:100%; height:100%; display:flex; align-items:center;';
                    var pct = params.value || 0;
                    var bar = document.createElement('div');
                    bar.style.cssText = 'position:absolute; left:0; top:15%; height:70%; width:' + pct + '%; background:#7ED321; opacity:0.3; border-radius:2px;';
                    var label = document.createElement('span');
                    label.style.cssText = 'position:relative; z-index:1; font-weight:600; font-size:12px; padding-left:6px;';
                    label.innerText = pct.toFixed(1) + '%';
                    this.eGui.appendChild(bar);
                    this.eGui.appendChild(label);
                }
                getGui() { return this.eGui; }
            }
        """)
        pct_concorrencia_renderer = JsCode("""
            class PctConcorrenciaRenderer {
                init(params) {
                    this.eGui = document.createElement('div');
                    this.eGui.style.cssText = 'position:relative; width:100%; height:100%; display:flex; align-items:center;';
                    var pct = params.value || 0;
                    var bar = document.createElement('div');
                    bar.style.cssText = 'position:absolute; left:0; top:15%; height:70%; width:' + pct + '%; background:#4A90D9; opacity:0.3; border-radius:2px;';
                    var label = document.createElement('span');
                    label.style.cssText = 'position:relative; z-index:1; font-weight:600; font-size:12px; padding-left:6px;';
                    label.innerText = pct.toFixed(1) + '%';
                    this.eGui.appendChild(bar);
                    this.eGui.appendChild(label);
                }
                getGui() { return this.eGui; }
            }
        """)

        mix_css = {
            ".header-stine": {"background-color": "rgba(126,211,33,0.25) !important", "color": "#4a7a00 !important", "font-weight": "700 !important"},
            ".header-concorrencia": {"background-color": "rgba(74,144,217,0.2) !important", "color": "#1a4d8a !important", "font-weight": "700 !important"},
            ".header-pct-stine": {"background-color": "rgba(126,211,33,0.15) !important", "color": "#4a7a00 !important", "font-weight": "700 !important"},
            ".header-pct-conc": {"background-color": "rgba(74,144,217,0.12) !important", "color": "#1a4d8a !important", "font-weight": "700 !important"},
        }

        gb_mix = GridOptionsBuilder.from_dataframe(mix_tabela)
        gb_mix.configure_default_column(resizable=True, sortable=True, filter=True)
        if "STINE" in mix_tabela.columns:
            gb_mix.configure_column("STINE", headerClass="header-stine")
        if "Concorrência" in mix_tabela.columns:
            gb_mix.configure_column("Concorrência", headerClass="header-concorrencia")
        gb_mix.configure_column("% STINE", type=["numericColumn"], cellRenderer=pct_stine_renderer, headerClass="header-pct-stine")
        gb_mix.configure_column("% Concorrência", type=["numericColumn"], cellRenderer=pct_concorrencia_renderer, headerClass="header-pct-conc")
        AgGrid(mix_tabela, gridOptions=gb_mix.build(),
               fit_columns_on_grid_load=True, height=350,
               allow_unsafe_jscode=True, theme="alpine",
               custom_css=mix_css)
    else:
        st.markdown("""
            <div style='padding: 24px 0px; margin-top: 8px;'>
                <p style='color: #888; font-size: 13px; text-align: center;'>
                    📊 Selecione ao menos uma <b>Regional</b> no filtro para visualizar o mix de materiais por RC.
                </p>
            </div>
        """, unsafe_allow_html=True)

    # ── Seção Distribuição Geográfica e Faixa de Área ────────
    st.markdown("""
        <div style="margin: 24px 0 20px 0;">
            <p style="margin: 0 0 6px 0; font-size: 11px; font-weight: 700; color: #1a1a1a; letter-spacing: 2px; text-transform: uppercase;">Distribuição Geográfica e Perfil do Produtor</p>
            <h2 style="margin: 0 0 8px 0; font-size: 26px; font-weight: 800; color: #1a1a1a; line-height: 1.2;">Quem são e onde estão os produtores</h2>
            <p style="margin: 0; font-size: 14px; color: #666; line-height: 1.6; max-width: 860px;">Mapa de distribuição das áreas e perfil das propriedades por potencial de cultivo. Entenda a concentração geográfica e o perfil dos produtores na carteira.</p>
        </div>
    """, unsafe_allow_html=True)

    cores_cidades = [
        ("#1a6bbd", "#dbeafe"), ("#15803d", "#dcfce7"), ("#7e22ce", "#f3e8ff"),
        ("#c2410c", "#ffedd5"), ("#0f766e", "#ccfbf1"), ("#be185d", "#fce7f3"),
        ("#92400e", "#fef3c7"),
    ]

    def mini_card_cidade(valor, label, cor_texto, cor_fundo):
        return f"""
            <div style="
                background-color: {cor_fundo};
                border-radius: 10px;
                padding: 16px 12px;
                text-align: center;
                height: 90px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            ">
                <p style="margin:0; font-size:28px; font-weight:700; color:{cor_texto};">{valor}</p>
                <p style="margin:4px 0 0 0; font-size:12px; color:{cor_texto}; font-weight:500;">{label}</p>
            </div>
        """

    # ── Bloco 1: Distribuição Geográfica ─────────────────────
    st.markdown("""
        <div style="margin: 8px 0 12px 0; padding-left: 12px; border-left: 4px solid #333;">
            <p style="margin:0; font-size:14px; font-weight:700; color:#212121;">
                Distribuição Geográfica das Áreas
            </p>
        </div>
    """, unsafe_allow_html=True)

    top_cidades = (
        df_filtrado.groupby("cidade_nome")
        .size()
        .reset_index(name="qtd")
        .sort_values("qtd", ascending=False)
        .head(6)
    )
    outras = df_filtrado.shape[0] - top_cidades["qtd"].sum()
    n_outras_cidades = df_filtrado["cidade_nome"].nunique() - len(top_cidades)

    colunas_cid = st.columns(7)
    for i, (_, row) in enumerate(top_cidades.iterrows()):
        cor_txt, cor_bg = cores_cidades[i % len(cores_cidades)]
        with colunas_cid[i]:
            st.markdown(mini_card_cidade(row["qtd"], row["cidade_nome"], cor_txt, cor_bg), unsafe_allow_html=True)

    if outras > 0:
        cor_txt, cor_bg = cores_cidades[6]
        with colunas_cid[6]:
            st.markdown(mini_card_cidade(outras, f"Outras {n_outras_cidades} cidades", cor_txt, cor_bg), unsafe_allow_html=True)

    # ── Tabela detalhada por cidade ───────────────────────────
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    cidade_tabela = df_filtrado.groupby(["cidade_nome", "estado_nome"]).agg(
        Áreas=("resultado_uuid", "count"),
        Produtores=("fazenda_produtor_uuid", "nunique"),
        Com_Resultado=("status_ensaio", lambda x: (x == "Com Resultado").sum()),
        Pot_Soja=("fazenda_area_plantada_soja", "sum"),
        Pot_Milho=("fazenda_area_plantada_milho", "sum"),
    ).reset_index()

    cidade_tabela["Pot_Total"] = cidade_tabela["Pot_Soja"] + cidade_tabela["Pot_Milho"]
    cidade_tabela["% Resultado"] = (cidade_tabela["Com_Resultado"] / cidade_tabela["Áreas"] * 100).round(1)
    cidade_tabela["Pot. Soja (ha)"] = cidade_tabela["Pot_Soja"].round(0).astype(int)
    cidade_tabela["Pot. Milho (ha)"] = cidade_tabela["Pot_Milho"].round(0).astype(int)
    cidade_tabela["Pot. Total (ha)"] = cidade_tabela["Pot_Total"].round(0).astype(int)
    cidade_tabela = cidade_tabela.sort_values("Áreas", ascending=False)
    cidade_tabela = cidade_tabela.rename(columns={"cidade_nome": "Cidade", "estado_nome": "Estado"})
    cidade_tabela = cidade_tabela[["Cidade", "Estado", "Produtores", "Áreas", "Com_Resultado", "Pot. Soja (ha)", "Pot. Milho (ha)", "Pot. Total (ha)", "% Resultado"]]
    cidade_tabela = cidade_tabela.rename(columns={"Com_Resultado": "Com Resultado"})

    pct_cidade_renderer = JsCode("""
        class PctCidadeRenderer {
            init(params) {
                this.eGui = document.createElement('div');
                this.eGui.style.cssText = 'position:relative; width:100%; height:100%; display:flex; align-items:center;';
                var pct = params.value || 0;
                var bar = document.createElement('div');
                bar.style.cssText = 'position:absolute; left:0; top:15%; height:70%; width:' + pct + '%; background:#009D57; opacity:0.25; border-radius:2px;';
                var label = document.createElement('span');
                label.style.cssText = 'position:relative; z-index:1; font-weight:600; font-size:12px; padding-left:6px;';
                label.innerText = pct.toFixed(1) + '%';
                this.eGui.appendChild(bar);
                this.eGui.appendChild(label);
            }
            getGui() { return this.eGui; }
        }
    """)

    cidade_css = {
        ".header-pot-soja": {"background-color": "rgba(0,157,87,0.2) !important", "color": "#004d2a !important", "font-weight": "700 !important"},
        ".header-pot-milho": {"background-color": "rgba(0,95,174,0.18) !important", "color": "#00336b !important", "font-weight": "700 !important"},
        ".header-com-resultado": {"background-color": "rgba(126,211,33,0.25) !important", "color": "#3a6200 !important", "font-weight": "700 !important"},
    }

    gb_cidade = GridOptionsBuilder.from_dataframe(cidade_tabela)
    gb_cidade.configure_default_column(resizable=True, sortable=True, filter=True)
    gb_cidade.configure_column("Com Resultado", headerClass="header-com-resultado")
    gb_cidade.configure_column("Pot. Soja (ha)", headerClass="header-pot-soja",
        valueFormatter="value.toLocaleString('pt-BR')")
    gb_cidade.configure_column("Pot. Milho (ha)", headerClass="header-pot-milho",
        valueFormatter="value.toLocaleString('pt-BR')")
    gb_cidade.configure_column("Pot. Total (ha)",
        valueFormatter="value.toLocaleString('pt-BR')")
    gb_cidade.configure_column("% Resultado", type=["numericColumn"], cellRenderer=pct_cidade_renderer)
    AgGrid(cidade_tabela, gridOptions=gb_cidade.build(),
           fit_columns_on_grid_load=True, height=520,
           allow_unsafe_jscode=True, theme="alpine",
           custom_css=cidade_css)


    # ── Visão Hierárquica Regional → Cidade ──────────────────
    st.markdown("""
        <div style="margin: 32px 0 16px 0;">
            <p style="margin: 0 0 6px 0; font-size: 11px; font-weight: 700; color: #1a1a1a; letter-spacing: 2px; text-transform: uppercase;">Drilldown por Regional</p>
            <h2 style="margin: 0 0 8px 0; font-size: 26px; font-weight: 800; color: #1a1a1a; line-height: 1.2;">Visão hierárquica das áreas</h2>
            <p style="margin: 0; font-size: 14px; color: #666; line-height: 1.6; max-width: 860px;">Navegue pela estrutura regional e entenda onde estão concentrados os ensaios. Expanda cada regional para ver as principais cidades, o RC responsável e o produtor com maior volume de ensaios.</p>
        </div>
    """, unsafe_allow_html=True)
    render_visao_hierarquica_regional(df_filtrado)

    # ── Bloco 2: Faixa de Área ───────────────────────────────
    st.markdown("""
        <div style="margin: 28px 0 12px 0; padding-left: 12px; border-left: 4px solid #333;">
            <p style="margin:0; font-size:14px; font-weight:700; color:#212121;">
                Áreas por Perfil de Potencial do Produtor
            </p>
        </div>
    """, unsafe_allow_html=True)

    if sel_cultura in ("Soja", "Milho"):
        col_faixa = "faixa_area_soja" if sel_cultura == "Soja" else "faixa_area_milho"

    faixas_ordem = [
        "Até 50 ha",
        "50 a 200 ha",
        "200 a 500 ha",
        "500 a 2.500 ha",
        "Acima de 2.500 ha",
    ]

    soja_qtd  = [df_filtrado[df_filtrado["faixa_area_soja"]  == f].shape[0] for f in faixas_ordem]
    milho_qtd = [df_filtrado[df_filtrado["faixa_area_milho"] == f].shape[0] for f in faixas_ordem]

    total_soja  = sum(soja_qtd)  or 1
    total_milho = sum(milho_qtd) or 1

    soja_rotulo  = [f"{q} ({round(q/total_soja*100,1)}%)"  for q in soja_qtd]
    milho_rotulo = [f"{q} ({round(q/total_milho*100,1)}%)" for q in milho_qtd]

    fig_faixa = go.Figure()

    fig_faixa.add_trace(go.Bar(
        y=faixas_ordem,
        x=[-q for q in soja_qtd],
        orientation="h",
        name="Soja",
        text=soja_rotulo,
        textposition="outside",
        marker_color="#009D57",
        textfont=dict(color="black", size=11)
    ))

    fig_faixa.add_trace(go.Bar(
        y=faixas_ordem,
        x=milho_qtd,
        orientation="h",
        name="Milho",
        text=milho_rotulo,
        textposition="outside",
        marker_color="#005FAE",
        textfont=dict(color="black", size=11)
    ))

    max_val = max(max(soja_qtd), max(milho_qtd)) * 1.4

    fig_faixa.update_layout(
        height=300,
        title_text="Distribuição por Perfil de Potencial — Soja vs Milho",
        title_x=0,
        title_font_size=14,
        title_font_color="black",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        barmode="overlay",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            font=dict(color="black", size=12)
        ),
        margin=dict(l=20, r=20, t=50, b=60),
        yaxis=dict(
            tickfont=dict(color="black", size=12),
            categoryorder="array",
            categoryarray=faixas_ordem
        ),
        xaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=True,
            zerolinecolor="black",
            zerolinewidth=1.5,
            range=[-max_val, max_val]
        ),
    )
    st.plotly_chart(fig_faixa, use_container_width=True)

    # ── Tabela por Perfil de Potencial ────────────────────────
    faixa_rows = []
    for f in faixas_ordem:
        s = df_filtrado[df_filtrado["faixa_area_soja"] == f].shape[0]
        m = df_filtrado[df_filtrado["faixa_area_milho"] == f].shape[0]
        total = s + m
        faixa_rows.append({
            "Perfil de Potencial": f,
            "Soja": s,
            "Milho": m,
            "Total": total,
            "% Soja": round(s / total * 100, 1) if total > 0 else 0.0,
            "% Milho": round(m / total * 100, 1) if total > 0 else 0.0,
        })
    faixa_tabela = pd.DataFrame(faixa_rows)

    # ── Indicador: % ensaios em faixas de alto potencial ─────
    faixas_alto = ["500 a 2.500 ha", "Acima de 2.500 ha"]
    ensaios_alto_soja  = df_filtrado[df_filtrado["faixa_area_soja"].isin(faixas_alto)].shape[0]
    ensaios_alto_milho = df_filtrado[df_filtrado["faixa_area_milho"].isin(faixas_alto)].shape[0]
    total_soja_faixa   = df_filtrado["faixa_area_soja"].notna().sum()
    total_milho_faixa  = df_filtrado["faixa_area_milho"].notna().sum()
    pct_alto_soja  = round(ensaios_alto_soja  / total_soja_faixa  * 100, 1) if total_soja_faixa  > 0 else 0
    pct_alto_milho = round(ensaios_alto_milho / total_milho_faixa * 100, 1) if total_milho_faixa > 0 else 0

    # Faixa dominante — mesma lógica da tabela (contagem de ensaios por faixa)
    soja_por_faixa  = {f: df_filtrado[df_filtrado["faixa_area_soja"]  == f].shape[0] for f in faixas_ordem}
    milho_por_faixa = {f: df_filtrado[df_filtrado["faixa_area_milho"] == f].shape[0] for f in faixas_ordem}
    faixa_dom_soja  = max(soja_por_faixa,  key=soja_por_faixa.get)  if any(soja_por_faixa.values())  else "—"
    faixa_dom_milho = max(milho_por_faixa, key=milho_por_faixa.get) if any(milho_por_faixa.values()) else "—"
    n_dom_soja  = soja_por_faixa[faixa_dom_soja]   if faixa_dom_soja  != "—" else 0
    n_dom_milho = milho_por_faixa[faixa_dom_milho] if faixa_dom_milho != "—" else 0

    cor_alto_soja  = "#0891B2"
    cor_alto_milho = "#0891B2"

    st.markdown(f"""
        <div style="display:flex; gap:16px; margin: 0 0 16px 0;">
            <div style="flex:1; background:white; border-radius:8px; padding:16px 20px;
                        box-shadow:0 2px 6px rgba(0,0,0,0.06); border-left:4px solid {cor_alto_soja};">
                <p style="margin:0 0 4px 0; font-size:11px; font-weight:700; color:#888; letter-spacing:1px; text-transform:uppercase;">
                    🌱 Soja — Perfil com Mais Áreas
                </p>
                <p style="margin:0; font-size:32px; font-weight:800; color:{cor_alto_soja};">{n_dom_soja}</p>
                <p style="margin:4px 0 0 0; font-size:13px; color:#555; font-weight:600;">{faixa_dom_soja}</p>
            </div>
            <div style="flex:1; background:white; border-radius:8px; padding:16px 20px;
                        box-shadow:0 2px 6px rgba(0,0,0,0.06); border-left:4px solid {cor_alto_milho};">
                <p style="margin:0 0 4px 0; font-size:11px; font-weight:700; color:#888; letter-spacing:1px; text-transform:uppercase;">
                    🌽 Milho — Perfil com Mais Áreas
                </p>
                <p style="margin:0; font-size:32px; font-weight:800; color:{cor_alto_milho};">{n_dom_milho}</p>
                <p style="margin:4px 0 0 0; font-size:13px; color:#555; font-weight:600;">{faixa_dom_milho}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    pct_faixa_soja = JsCode("""
        class PctFaixaSoja {
            init(params) {
                this.eGui = document.createElement('div');
                this.eGui.style.cssText = 'position:relative; width:100%; height:100%; display:flex; align-items:center;';
                var pct = params.value || 0;
                var bar = document.createElement('div');
                bar.style.cssText = 'position:absolute; left:0; top:15%; height:70%; width:' + pct + '%; background:#009D57; opacity:0.25; border-radius:2px;';
                var label = document.createElement('span');
                label.style.cssText = 'position:relative; z-index:1; font-weight:600; font-size:12px; padding-left:6px;';
                label.innerText = pct.toFixed(1) + '%';
                this.eGui.appendChild(bar);
                this.eGui.appendChild(label);
            }
            getGui() { return this.eGui; }
        }
    """)
    pct_faixa_milho = JsCode("""
        class PctFaixaMilho {
            init(params) {
                this.eGui = document.createElement('div');
                this.eGui.style.cssText = 'position:relative; width:100%; height:100%; display:flex; align-items:center;';
                var pct = params.value || 0;
                var bar = document.createElement('div');
                bar.style.cssText = 'position:absolute; left:0; top:15%; height:70%; width:' + pct + '%; background:#005FAE; opacity:0.25; border-radius:2px;';
                var label = document.createElement('span');
                label.style.cssText = 'position:relative; z-index:1; font-weight:600; font-size:12px; padding-left:6px;';
                label.innerText = pct.toFixed(1) + '%';
                this.eGui.appendChild(bar);
                this.eGui.appendChild(label);
            }
            getGui() { return this.eGui; }
        }
    """)

    faixa_css = {
        ".header-soja-faixa": {"background-color": "rgba(0,157,87,0.25) !important", "color": "#004d2a !important", "font-weight": "700 !important"},
        ".header-milho-faixa": {"background-color": "rgba(0,95,174,0.2) !important", "color": "#00336b !important", "font-weight": "700 !important"},
        ".header-pct-soja-faixa": {"background-color": "rgba(0,157,87,0.15) !important", "color": "#004d2a !important", "font-weight": "700 !important"},
        ".header-pct-milho-faixa": {"background-color": "rgba(0,95,174,0.12) !important", "color": "#00336b !important", "font-weight": "700 !important"},
    }

    gb_faixa = GridOptionsBuilder.from_dataframe(faixa_tabela)
    gb_faixa.configure_default_column(resizable=True, sortable=True)
    gb_faixa.configure_column("Soja", headerClass="header-soja-faixa")
    gb_faixa.configure_column("Milho", headerClass="header-milho-faixa")
    gb_faixa.configure_column("% Soja", type=["numericColumn"], cellRenderer=pct_faixa_soja, headerClass="header-pct-soja-faixa")
    gb_faixa.configure_column("% Milho", type=["numericColumn"], cellRenderer=pct_faixa_milho, headerClass="header-pct-milho-faixa")
    AgGrid(faixa_tabela, gridOptions=gb_faixa.build(),
           fit_columns_on_grid_load=True, height=360,
           allow_unsafe_jscode=True, theme="alpine",
           custom_css=faixa_css)


# ═══════════════════════════════════════════════════════════
# PÁGINA: PERFORMANCE DE MATERIAIS
# ═══════════════════════════════════════════════════════════
elif st.session_state["pagina"] == "performance":
    from performance import render_performance
    render_performance(df_filtrado, card, cores_mix, cores_cultura, COR_SOJA, COR_MILHO, filtro_ativo, sel_cultura, render_visao_hierarquica_regional)