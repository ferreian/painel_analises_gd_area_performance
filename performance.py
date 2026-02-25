import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render_performance(df_filtrado, card, cores_mix, cores_cultura, COR_SOJA, COR_MILHO, filtro_ativo, sel_cultura, render_visao_hierarquica_regional):

    # ── KPIs ─────────────────────────────────────────────────
    total_areas    = df_filtrado["resultado_uuid"].nunique()
    total_clientes = df_filtrado["fazenda_produtor_uuid"].nunique()
    com_resultado  = df_filtrado[df_filtrado["status_ensaio"] == "Com Resultado"].shape[0]
    aguardando     = df_filtrado[df_filtrado["status_ensaio"] == "Aguardando Colheita"].shape[0]

    pct_resultado  = round(com_resultado / total_areas * 100, 1) if total_areas > 0 else 0
    pct_aguardando = round(aguardando    / total_areas * 100, 1) if total_areas > 0 else 0


    produtores_unicos = df_filtrado.drop_duplicates(subset="fazenda_produtor_uuid")
    cobertura_gd  = round(total_areas / total_clientes, 1) if total_clientes > 0 else 0
    pot_soja      = int(produtores_unicos["fazenda_area_plantada_soja"].fillna(0).sum())
    pot_milho     = int(produtores_unicos["fazenda_area_plantada_milho"].fillna(0).sum())
    n_prod        = len(produtores_unicos)
    media_soja    = round(pot_soja  / n_prod, 1) if n_prod > 0 else 0
    media_milho   = round(pot_milho / n_prod, 1) if n_prod > 0 else 0

    def fmt_ha(valor):
        if valor >= 1_000_000:
            return f"{valor/1_000_000:.2f}M ha".replace(".", ",")
        elif valor >= 1_000:
            return f"{valor/1_000:.1f}K ha".replace(".", ",")
        return f"{valor:,} ha".replace(",", ".")

    # ── Título infográfico acima dos cards ───────────────────
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

    # ── Cards KPI ─────────────────────────────────────────────
    col0, col1, colg1, col2, colg2, col3, colg3, col4, colg4, col5, colg5, col6, col_end = st.columns(
        [0.5, 3, 0.3, 3, 0.3, 3, 0.3, 3, 0.3, 3, 0.3, 3, 0.5]
    )

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

    # ════════════════════════════════════════════════════════
    # MARCHA DE PLANTIO
    # ════════════════════════════════════════════════════════

    st.markdown("""
        <div style="margin: 32px 0 12px 0;">
            <p style="margin: 0 0 4px 0; font-size: 11px; font-weight: 700; color: #1a1a1a; letter-spacing: 2px; text-transform: uppercase;">Avanço de Plantio</p>
            <div style="margin:0 0 8px 0; font-size:26px; font-weight:800; color:#1a1a1a; line-height:1.2;">Marcha de Plantio</div>
            <p style="margin: 0; font-size: 14px; color: #666; line-height: 1.6; max-width: 860px;">Evolução semanal do percentual acumulado de áreas plantadas. O tamanho de cada ponto representa a quantidade de áreas plantadas naquela semana.</p>
        </div>
    """, unsafe_allow_html=True)

    # ── Filtra apenas áreas com data de plantio preenchida ───
    df_plantio = df_filtrado[df_filtrado["resultado_data_plantio_dt"].notna()].copy()

    if len(df_plantio) == 0:
        st.info("Nenhuma área com data de plantio registrada para os filtros selecionados.")
    else:
        try:
            total_com_data = len(df_plantio)

            # Agrupa por semana
            df_plantio["semana"] = df_plantio["resultado_data_plantio_dt"].dt.to_period("W").dt.start_time
            semanas = (
                df_plantio.groupby("semana")
                .size()
                .reset_index(name="qtd_semana")
                .sort_values("semana")
            )
            semanas["acumulado"]    = semanas["qtd_semana"].cumsum()
            semanas["pct_acum"]     = (semanas["acumulado"] / total_com_data * 100).round(1)
            semanas["semana_label"] = semanas["semana"].dt.strftime("%d/%b").str.lstrip("0")

            fig = go.Figure()

            # ── Sombreados de zona ────────────────────────────────
            fig.add_shape(type="rect",
                xref="paper", yref="y",
                x0=0, x1=1, y0=0, y1=50,
                fillcolor="rgba(220,38,38,0.07)",
                line_width=0, layer="below"
            )
            fig.add_shape(type="rect",
                xref="paper", yref="y",
                x0=0, x1=1, y0=50, y1=90,
                fillcolor="rgba(217,119,6,0.07)",
                line_width=0, layer="below"
            )
            fig.add_shape(type="rect",
                xref="paper", yref="y",
                x0=0, x1=1, y0=90, y1=100,
                fillcolor="rgba(126,211,33,0.10)",
                line_width=0, layer="below"
            )

            # Linhas de referência 50% e 90%
            fig.add_shape(type="line",
                xref="paper", yref="y",
                x0=0, x1=1, y0=50, y1=50,
                line=dict(color="rgba(217,119,6,0.5)", width=1.5, dash="dot"),
                layer="below"
            )
            fig.add_shape(type="line",
                xref="paper", yref="y",
                x0=0, x1=1, y0=90, y1=90,
                line=dict(color="rgba(126,211,33,0.6)", width=1.5, dash="dot"),
                layer="below"
            )

            # Anotações das zonas
            fig.add_annotation(x=1, xref="paper", y=25, yref="y",
                text="<b>Início</b>", showarrow=False,
                xanchor="left", font=dict(size=11, color="rgba(220,38,38,0.5)"), xshift=8)
            fig.add_annotation(x=1, xref="paper", y=70, yref="y",
                text="<b>Progresso</b>", showarrow=False,
                xanchor="left", font=dict(size=11, color="rgba(217,119,6,0.6)"), xshift=8)
            fig.add_annotation(x=1, xref="paper", y=95, yref="y",
                text="<b>Fim</b>", showarrow=False,
                xanchor="left", font=dict(size=11, color="rgba(100,180,50,0.8)"), xshift=8)

            # ── Linha conectando os pontos ────────────────────
            fig.add_trace(go.Scatter(
                x=semanas["semana"],
                y=semanas["pct_acum"],
                mode="lines",
                line=dict(color="rgba(0,95,174,0.3)", width=2),
                showlegend=False,
                hoverinfo="skip"
            ))

            # ── Dots com tamanho proporcional ─────────────────
            qtd_max = semanas["qtd_semana"].max()
            qtd_min = semanas["qtd_semana"].min()

            def escala_dot(q):
                if qtd_max == qtd_min:
                    return 28
                return 14 + (q - qtd_min) / (qtd_max - qtd_min) * 34

            def cor_dot(pct):
                if pct >= 90:
                    return "#7ED321"
                elif pct >= 50:
                    return "#D97706"
                return "#DC2626"

            semanas["dot_size"] = semanas["qtd_semana"].apply(escala_dot)
            semanas["dot_cor"]  = semanas["pct_acum"].apply(cor_dot)

            fig.add_trace(go.Scatter(
                x=semanas["semana"],
                y=semanas["pct_acum"],
                mode="markers+text",
                marker=dict(
                    size=semanas["dot_size"],
                    color=semanas["dot_cor"],
                    opacity=0.85,
                    line=dict(color="white", width=2)
                ),
                text=semanas["pct_acum"].apply(lambda v: f"{v}%"),
                textposition="top center",
                textfont=dict(size=11, color="black"),
                customdata=semanas[["qtd_semana", "acumulado", "semana_label"]],
                hovertemplate=(
                    "<b>Semana de %{customdata[2]}</b><br>"
                    "%{customdata[0]} áreas plantadas<br>"
                    "Acumulado: %{customdata[1]} áreas (%{y}%)<extra></extra>"
                ),
                showlegend=False
            ))

            fig.update_layout(
                height=420,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=80, t=40, b=60),
                xaxis=dict(
                    title="",
                    tickformat="%d/%b",
                    tickfont=dict(color="black", size=11),
                    showgrid=False,
                    zeroline=False,
                ),
                yaxis=dict(
                    title="% acumulado",
                    range=[-5, 112],
                    ticksuffix="%",
                    tickvals=[0, 20, 40, 60, 80, 100],
                    tickfont=dict(color="black", size=11),
                    showgrid=True,
                    gridcolor="rgba(0,0,0,0.05)",
                    zeroline=False,
                ),
            )

            st.plotly_chart(fig, use_container_width=True)

            # ── Resumo rápido abaixo do gráfico ──────────────
            semana_50   = semanas[semanas["pct_acum"] >= 50]["semana_label"].iloc[0] if (semanas["pct_acum"] >= 50).any() else "—"
            semana_90   = semanas[semanas["pct_acum"] >= 90]["semana_label"].iloc[0] if (semanas["pct_acum"] >= 90).any() else "Em andamento"
            semanas_tot = len(semanas)

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.markdown(card("Áreas com data de plantio", f"{total_com_data:,}".replace(",", "."), "registradas no período", "#005FAE"), unsafe_allow_html=True)
            with col_r2:
                st.markdown(card("Semanas de plantio", f"{semanas_tot}", "semanas com atividade", "#7C3AED"), unsafe_allow_html=True)
            with col_r3:
                st.markdown(card("50% atingido na semana de", semana_50, "metade das áreas plantadas", "#D97706"), unsafe_allow_html=True)
            with col_r4:
                cor_90 = "#7ED321" if semana_90 != "Em andamento" else "#DC2626"
                st.markdown(card("90% atingido na semana de", semana_90, "plantio quase completo", cor_90), unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro ao gerar gráfico de marcha de plantio: {e}")
            import traceback
            st.code(traceback.format_exc())

    # ════════════════════════════════════════════════════════
    # MARCHA DE COLHEITA
    # ════════════════════════════════════════════════════════

    st.markdown("""
        <div style="margin: 32px 0 12px 0;">
            <p style="margin: 0 0 4px 0; font-size: 11px; font-weight: 700; color: #1a1a1a; letter-spacing: 2px; text-transform: uppercase;">Avanço de Colheita</p>
            <div style="margin:0 0 8px 0; font-size:26px; font-weight:800; color:#1a1a1a; line-height:1.2;">Marcha de Colheita</div>
            <p style="margin: 0; font-size: 14px; color: #666; line-height: 1.6; max-width: 860px;">Evolução semanal do percentual acumulado de áreas colhidas. O tamanho de cada ponto representa a quantidade de áreas colhidas naquela semana.</p>
        </div>
    """, unsafe_allow_html=True)

    df_colheita = df_filtrado[df_filtrado["resultado_data_colheita_dt"].notna()].copy()

    if len(df_colheita) == 0:
        st.info("Nenhuma área com data de colheita registrada para os filtros selecionados.")
    else:
        try:
            total_com_colheita = len(df_colheita)

            df_colheita["semana"] = df_colheita["resultado_data_colheita_dt"].dt.to_period("W").dt.start_time
            semanas_c = (
                df_colheita.groupby("semana")
                .size()
                .reset_index(name="qtd_semana")
                .sort_values("semana")
            )
            semanas_c["acumulado"]    = semanas_c["qtd_semana"].cumsum()
            semanas_c["pct_acum"]     = (semanas_c["acumulado"] / total_com_colheita * 100).round(1)
            semanas_c["semana_label"] = semanas_c["semana"].dt.strftime("%d/%b").str.lstrip("0")

            fig_c = go.Figure()

            # ── Sombreados de zona ────────────────────────────
            fig_c.add_shape(type="rect",
                xref="paper", yref="y",
                x0=0, x1=1, y0=0, y1=50,
                fillcolor="rgba(220,38,38,0.07)",
                line_width=0, layer="below"
            )
            fig_c.add_shape(type="rect",
                xref="paper", yref="y",
                x0=0, x1=1, y0=50, y1=90,
                fillcolor="rgba(217,119,6,0.07)",
                line_width=0, layer="below"
            )
            fig_c.add_shape(type="rect",
                xref="paper", yref="y",
                x0=0, x1=1, y0=90, y1=100,
                fillcolor="rgba(126,211,33,0.10)",
                line_width=0, layer="below"
            )

            # Linhas de referência
            fig_c.add_shape(type="line",
                xref="paper", yref="y",
                x0=0, x1=1, y0=50, y1=50,
                line=dict(color="rgba(217,119,6,0.5)", width=1.5, dash="dot"),
                layer="below"
            )
            fig_c.add_shape(type="line",
                xref="paper", yref="y",
                x0=0, x1=1, y0=90, y1=90,
                line=dict(color="rgba(126,211,33,0.6)", width=1.5, dash="dot"),
                layer="below"
            )

            # Anotações das zonas
            fig_c.add_annotation(x=1, xref="paper", y=25, yref="y",
                text="<b>Início</b>", showarrow=False,
                xanchor="left", font=dict(size=11, color="rgba(220,38,38,0.5)"), xshift=8)
            fig_c.add_annotation(x=1, xref="paper", y=70, yref="y",
                text="<b>Progresso</b>", showarrow=False,
                xanchor="left", font=dict(size=11, color="rgba(217,119,6,0.6)"), xshift=8)
            fig_c.add_annotation(x=1, xref="paper", y=95, yref="y",
                text="<b>Fim</b>", showarrow=False,
                xanchor="left", font=dict(size=11, color="rgba(100,180,50,0.8)"), xshift=8)

            # Linha conectando os pontos
            fig_c.add_trace(go.Scatter(
                x=semanas_c["semana"],
                y=semanas_c["pct_acum"],
                mode="lines",
                line=dict(color="rgba(0,157,87,0.3)", width=2),
                showlegend=False,
                hoverinfo="skip"
            ))

            # Dots com tamanho proporcional
            qtd_max_c = semanas_c["qtd_semana"].max()
            qtd_min_c = semanas_c["qtd_semana"].min()

            def escala_dot_c(q):
                if qtd_max_c == qtd_min_c:
                    return 28
                return 14 + (q - qtd_min_c) / (qtd_max_c - qtd_min_c) * 34

            def cor_dot_c(pct):
                if pct >= 90:
                    return "#7ED321"
                elif pct >= 50:
                    return "#D97706"
                return "#DC2626"

            semanas_c["dot_size"] = semanas_c["qtd_semana"].apply(escala_dot_c)
            semanas_c["dot_cor"]  = semanas_c["pct_acum"].apply(cor_dot_c)

            fig_c.add_trace(go.Scatter(
                x=semanas_c["semana"],
                y=semanas_c["pct_acum"],
                mode="markers+text",
                marker=dict(
                    size=semanas_c["dot_size"],
                    color=semanas_c["dot_cor"],
                    opacity=0.85,
                    line=dict(color="white", width=2)
                ),
                text=semanas_c["pct_acum"].apply(lambda v: f"{v}%"),
                textposition="top center",
                textfont=dict(size=11, color="black"),
                customdata=semanas_c[["qtd_semana", "acumulado", "semana_label"]],
                hovertemplate=(
                    "<b>Semana de %{customdata[2]}</b><br>"
                    "%{customdata[0]} áreas colhidas<br>"
                    "Acumulado: %{customdata[1]} áreas (%{y}%)<extra></extra>"
                ),
                showlegend=False
            ))

            fig_c.update_layout(
                height=420,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=80, t=40, b=60),
                xaxis=dict(
                    title="",
                    tickformat="%d/%b",
                    tickfont=dict(color="black", size=11),
                    showgrid=False,
                    zeroline=False,
                ),
                yaxis=dict(
                    title="% acumulado",
                    range=[-5, 112],
                    ticksuffix="%",
                    tickvals=[0, 20, 40, 60, 80, 100],
                    tickfont=dict(color="black", size=11),
                    showgrid=True,
                    gridcolor="rgba(0,0,0,0.05)",
                    zeroline=False,
                ),
            )

            st.plotly_chart(fig_c, use_container_width=True)

            # Resumo rápido
            semana_50_c   = semanas_c[semanas_c["pct_acum"] >= 50]["semana_label"].iloc[0] if (semanas_c["pct_acum"] >= 50).any() else "—"
            semana_90_c   = semanas_c[semanas_c["pct_acum"] >= 90]["semana_label"].iloc[0] if (semanas_c["pct_acum"] >= 90).any() else "Em andamento"
            semanas_tot_c = len(semanas_c)

            col_c1, col_c2, col_c3, col_c4 = st.columns(4)
            with col_c1:
                st.markdown(card("Áreas com data de colheita", f"{total_com_colheita:,}".replace(",", "."), "registradas no período", "#009D57"), unsafe_allow_html=True)
            with col_c2:
                st.markdown(card("Semanas de colheita", f"{semanas_tot_c}", "semanas com atividade", "#7C3AED"), unsafe_allow_html=True)
            with col_c3:
                st.markdown(card("50% atingido na semana de", semana_50_c, "metade das áreas colhidas", "#D97706"), unsafe_allow_html=True)
            with col_c4:
                cor_90_c = "#7ED321" if semana_90_c != "Em andamento" else "#DC2626"
                st.markdown(card("90% atingido na semana de", semana_90_c, "colheita quase completa", cor_90_c), unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro ao gerar gráfico de marcha de colheita: {e}")
            import traceback
            st.code(traceback.format_exc())

    # ════════════════════════════════════════════════════════
    # GRADIENT CHART — PERFORMANCE DOS MATERIAIS
    # ════════════════════════════════════════════════════════

    st.markdown("""
        <div style="margin: 32px 0 12px 0;">
            <p style="margin: 0 0 4px 0; font-size: 11px; font-weight: 700; color: #1a1a1a; letter-spacing: 2px; text-transform: uppercase;">Distribuição de Resultados</p>
            <div style="margin:0 0 8px 0; font-size:26px; font-weight:800; color:#1a1a1a; line-height:1.2;">Performance dos Materiais</div>
            <p style="margin: 0; font-size: 14px; color: #666; line-height: 1.6; max-width: 860px;">
                Cada barra mostra o intervalo de produtividade de um material — do pior ao melhor resultado registrado em campo.
                A <strong>faixa mais escura</strong> é onde estão a maioria dos resultados.
                A <strong>linha preta</strong> é a média.
                Barras <strong>mais estreitas</strong> indicam um material mais consistente.
                Barras <strong>mais largas</strong> indicam que o resultado varia muito dependendo da fazenda.
                Mínimo de 3 ensaios por material.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Base com resultado ────────────────────────────────────
    df_res = df_filtrado[
        (df_filtrado["status_ensaio"] == "Com Resultado") &
        (df_filtrado["resultado_prod_scha_corrigido"].notna())
    ].copy()
    df_res["resultado_prod_scha_corrigido"] = pd.to_numeric(df_res["resultado_prod_scha_corrigido"], errors="coerce")
    df_res = df_res[df_res["resultado_prod_scha_corrigido"].notna()]
    col_mat = "tratamentos_nome" if "tratamentos_nome" in df_res.columns else None

    if col_mat is None or len(df_res) == 0:
        st.info("Sem dados de resultado para gerar o gráfico de performance.")
    else:
        # ── Filtro 1: Cultura ─────────────────────────────────
        culturas_disp = sorted(df_res["cultura_nome"].dropna().unique().tolist())
        col_f1, col_f2, col_f3 = st.columns([1, 2, 2])

        with col_f1:
            cultura_sel = st.selectbox(
                "Cultura",
                options=culturas_disp,
                index=culturas_disp.index("Soja") if "Soja" in culturas_disp else 0,
                key="grad_cultura"
            )

        df_cult = df_res[df_res["cultura_nome"] == cultura_sel]
        cor_cultura = "0,157,87" if cultura_sel == "Soja" else "0,95,174"

        # Materiais com mínimo 3 ensaios
        contagem = df_cult.groupby(col_mat).size()
        mats_validos = contagem[contagem >= 3].index.tolist()

        df_cult_val = df_cult[df_cult[col_mat].isin(mats_validos)]

        stine_disp = sorted(
            df_cult_val[df_cult_val["categoria_material"] == "STINE"][col_mat].dropna().unique().tolist()
        )
        conc_disp = sorted(
            df_cult_val[df_cult_val["categoria_material"] == "Concorrência"][col_mat].dropna().unique().tolist()
        )

        # ── Filtro 2: STINE (obrigatório) ────────────────────
        with col_f2:
            stine_sel = st.multiselect(
                "Material STINE",
                options=stine_disp,
                default=[],
                placeholder="Selecione ao menos um cultivar STINE...",
                key="grad_stine"
            )

        # ── Filtro 3: Concorrência — só fazendas em comum ────
        if stine_sel:
            # Fazendas que têm ao menos um dos STINE selecionados
            fazendas_stine = df_cult_val[
                (df_cult_val[col_mat].isin(stine_sel)) &
                (df_cult_val["categoria_material"] == "STINE")
            ]["fazenda_produtor_uuid"].unique()

            # Concorrentes que aparecem nessas mesmas fazendas
            conc_disp = sorted(
                df_cult_val[
                    (df_cult_val["fazenda_produtor_uuid"].isin(fazendas_stine)) &
                    (df_cult_val["categoria_material"] == "Concorrência")
                ][col_mat].dropna().unique().tolist()
            )
        else:
            conc_disp = []

        with col_f3:
            conc_sel = st.multiselect(
                "Concorrência (opcional)",
                options=conc_disp,
                default=[],
                placeholder="Selecione concorrentes para comparar..." if stine_sel else "Selecione um STINE primeiro...",
                key="grad_conc",
                disabled=not stine_sel
            )

        # ── Filtros adicionais ────────────────────────────────
        with st.expander("⚙️ Filtros adicionais de ambiente"):
            col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns(5)

            # Base de referência para hierarquia dos filtros adicionais
            df_env = df_cult_val.copy()

            # ── 1. Irrigação ──────────────────────────────────
            with col_a1:
                st.markdown("<p style='margin:0 0 8px 0; font-size:13px; font-weight:600; color:black;'>Irrigação</p>", unsafe_allow_html=True)
                sequeiro_ativo = st.toggle("Sequeiro", value=True, key="grad_irrig")
                irrig_sel = ["Sequeiro"] if sequeiro_ativo else ["Irrigado"]

            if "irrigacao" in df_env.columns:
                df_env = df_env[df_env["irrigacao"].isin(irrig_sel)]

            # ── 2. Textura do Solo — depende de irrigação ─────
            with col_a2:
                st.markdown("<p style='margin:0 0 8px 0; font-size:13px; font-weight:600; color:black;'>Textura do Solo</p>", unsafe_allow_html=True)
                textura_opts = sorted(df_env["fazenda_textura_solo"].dropna().unique().tolist()) if "fazenda_textura_solo" in df_env.columns else []
                textura_sel  = [t for t in textura_opts if st.checkbox(t, value=True, key=f"grad_tex_{t}")]

            if "fazenda_textura_solo" in df_env.columns and textura_sel:
                df_env = df_env[df_env["fazenda_textura_solo"].isin(textura_sel)]

            # ── 3. Fertilidade — depende de irrigação + textura
            with col_a3:
                st.markdown("<p style='margin:0 0 8px 0; font-size:13px; font-weight:600; color:black;'>Fertilidade</p>", unsafe_allow_html=True)
                fertil_opts = sorted(df_env["fazenda_fertilidade_solo"].dropna().unique().tolist()) if "fazenda_fertilidade_solo" in df_env.columns else []
                fertil_sel  = [f for f in fertil_opts if st.checkbox(f, value=True, key=f"grad_fer_{f}")]

            if "fazenda_fertilidade_solo" in df_env.columns and fertil_sel:
                df_env = df_env[df_env["fazenda_fertilidade_solo"].isin(fertil_sel)]

            # ── 4. Investimento — depende de todos anteriores ─
            with col_a4:
                st.markdown("<p style='margin:0 0 8px 0; font-size:13px; font-weight:600; color:black;'>Nível de Investimento</p>", unsafe_allow_html=True)
                invest_opts = sorted(df_env["fazenda_nivel_investimento"].dropna().unique().tolist()) if "fazenda_nivel_investimento" in df_env.columns else []
                invest_sel  = [i for i in invest_opts if st.checkbox(i, value=True, key=f"grad_inv_{i}")]

            if "fazenda_nivel_investimento" in df_env.columns and invest_sel:
                df_env = df_env[df_env["fazenda_nivel_investimento"].isin(invest_sel)]

            # ── 5. Altitude — depende de todos anteriores ─────
            with col_a5:
                if "fazenda_altitude" in df_env.columns and df_env["fazenda_altitude"].notna().any():
                    alt_vals = df_env["fazenda_altitude"].dropna()
                    alt_min  = int(alt_vals.min())
                    alt_max  = int(alt_vals.max())
                    alt_sel  = st.slider("Altitude (m)", min_value=alt_min, max_value=alt_max, value=(alt_min, alt_max), key="grad_alt")
                else:
                    alt_sel = None

        # ── Gráfico só aparece com ao menos 1 STINE ──────────
        # Aplica filtros adicionais — df_env já tem irrigação, textura, fertilidade e investimento aplicados
        df_plot_base = df_env.copy()
        if alt_sel is not None and "fazenda_altitude" in df_plot_base.columns:
            df_plot_base = df_plot_base[
                (df_plot_base["fazenda_altitude"] >= alt_sel[0]) &
                (df_plot_base["fazenda_altitude"] <= alt_sel[1])
            ]
        if not stine_sel:
            st.markdown("""
                <div style="
                    background: white;
                    border-radius: 8px;
                    padding: 32px 20px;
                    text-align: center;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
                    margin-top: 16px;
                ">
                    <p style="margin:0; font-size:14px; color:#888;">
                        👆 Selecione ao menos um <strong>material STINE</strong> para visualizar o gráfico.
                    </p>
                </div>
            """, unsafe_allow_html=True)
        else:
            # ── Legenda das camadas ───────────────────────────
            st.markdown("""
                <div style="display:flex; gap:24px; align-items:center; margin: 12px 0 10px 0; flex-wrap:wrap;">
                    <span style="font-size:12px; font-weight:700; color:#555; text-transform:uppercase; letter-spacing:1px;">Como ler:</span>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="width:36px; height:14px; background:rgba(0,157,87,0.12); border-radius:2px;"></div>
                        <span style="font-size:12px; color:#333;">Pior ao melhor resultado registrado</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="width:36px; height:14px; background:rgba(0,157,87,0.28); border-radius:2px;"></div>
                        <span style="font-size:12px; color:#333;">Faixa mais comum de resultado</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="width:36px; height:14px; background:rgba(0,157,87,0.50); border-radius:2px;"></div>
                        <span style="font-size:12px; color:#333;">Onde estão a maioria dos resultados</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="width:36px; height:3px; background:#1a1a1a; border-radius:2px; margin: 6px 0;"></div>
                        <span style="font-size:12px; color:#333;">Média (n = nº de ensaios)</span>
                    </div>
                </div>
                <div style="
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    background: #fff8e1;
                    border: 1px solid #f59e0b;
                    border-radius: 6px;
                    padding: 7px 14px;
                    margin-bottom: 18px;
                ">
                    <span style="font-size:16px;">⚠️</span>
                    <span style="font-size:12px; color:#92400e; line-height:1.5;">
                        <strong>Atenção ao número de ensaios (n):</strong> materiais com poucos ensaios têm barras mais estreitas e médias menos confiáveis.
                        Quanto mais ensaios, mais representativo é o resultado.
                    </span>
                </div>
            """, unsafe_allow_html=True)
            mats_sel = stine_sel + conc_sel
            df_plot = df_plot_base[df_plot_base[col_mat].isin(mats_sel)]

            # Estatísticas por material
            stats = (
                df_plot.groupby([col_mat, "categoria_material"])["resultado_prod_scha_corrigido"]
                .agg(
                    n="count",
                    media="mean",
                    std="std",
                    minv="min",
                    maxv="max",
                    q1=lambda x: x.quantile(0.25),
                    q3=lambda x: x.quantile(0.75),
                )
                .reset_index()
            )
            stats["std"] = stats["std"].fillna(0)
            stats = stats.sort_values("media", ascending=True)
            cultivares = stats[col_mat].tolist()

            fig = go.Figure()

            for idx, row in stats.iterrows():
                nome     = row[col_mat]
                media    = row["media"]
                std      = row["std"]
                minv     = row["minv"]
                maxv     = row["maxv"]
                q1       = row["q1"]
                q3       = row["q3"]
                is_stine = row["categoria_material"] == "STINE"
                rgb      = cor_cultura if is_stine else "150,150,150"
                y_pos    = cultivares.index(nome)

                std_low  = max(media - std, minv)
                std_high = min(media + std, maxv)

                # Camada 1: min → max
                fig.add_trace(go.Bar(
                    y=[nome], x=[maxv - minv], base=[minv],
                    orientation="h",
                    width=0.55, showlegend=False, hoverinfo="skip",
                    marker=dict(color=f"rgba({rgb},0.12)", line_width=0)
                ))
                # Camada 2: média ± desvio
                fig.add_trace(go.Bar(
                    y=[nome], x=[std_high - std_low], base=[std_low],
                    orientation="h",
                    width=0.55, showlegend=False, hoverinfo="skip",
                    marker=dict(color=f"rgba({rgb},0.28)", line_width=0)
                ))
                # Camada 3: Q1 → Q3
                fig.add_trace(go.Bar(
                    y=[nome], x=[q3 - q1], base=[q1],
                    orientation="h",
                    width=0.55, showlegend=False, hoverinfo="skip",
                    marker=dict(color=f"rgba({rgb},0.50)", line_width=0)
                ))
                # Linha da média (vertical no eixo horizontal)
                fig.add_shape(
                    type="line",
                    y0=y_pos - 0.28, y1=y_pos + 0.28,
                    x0=media, x1=media,
                    xref="x", yref="y",
                    line=dict(color="#1a1a1a", width=2.5),
                    layer="above"
                )
                # Rótulo da média
                n_ensaios = int(row["n"])
                fig.add_annotation(
                    x=media, y=y_pos + 0.32,
                    text=f"<b>{media:.1f}</b> (n={n_ensaios})",
                    showarrow=False,
                    font=dict(size=13, color="#1a1a1a"),
                    xanchor="center",
                    yanchor="bottom",
                    bgcolor="rgba(255,255,255,0.75)",
                    borderpad=2,
                )

            # Hover
            fig.add_trace(go.Scatter(
                x=stats["media"],
                y=stats[col_mat],
                mode="markers",
                marker=dict(size=1, opacity=0),
                customdata=stats[["n", "media", "std", "minv", "maxv", "q1", "q3"]].values,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Ensaios: %{customdata[0]:.0f}<br>"
                    "Média: <b>%{customdata[1]:.1f} sc/ha</b><br>"
                    "Desvio padrão: %{customdata[2]:.1f}<br>"
                    "Mín: %{customdata[3]:.1f} | Máx: %{customdata[4]:.1f}<br>"
                    "Q1: %{customdata[5]:.1f} | Q3: %{customdata[6]:.1f}<extra></extra>"
                ),
                showlegend=False
            ))

            fig.update_layout(
                height=max(380, len(cultivares) * 44 + 80),
                barmode="overlay",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=40, t=10, b=50),
                xaxis=dict(
                    title=dict(text="<b>sc/ha</b>", font=dict(color="black", size=13)),
                    tickfont=dict(color="black", size=12, family="Arial Black"),
                    tickcolor="black",
                    showgrid=True,
                    gridcolor="rgba(0,0,0,0.06)",
                    zeroline=False,
                ),
                yaxis=dict(
                    tickfont=dict(color="black", size=12, family="Arial Black"),
                    tickcolor="black",
                    showgrid=False,
                    zeroline=False,
                    categoryorder="array",
                    categoryarray=cultivares,
                ),
                font=dict(color="black"),
            )
            st.plotly_chart(fig, use_container_width=True)

            # ════════════════════════════════════════════════
            # PERFORMANCE POR GEOGRAFIA
            # ════════════════════════════════════════════════
            st.markdown("""
                <div style="margin: 32px 0 12px 0;">
                    <p style="margin: 0 0 4px 0; font-size: 11px; font-weight: 700; color: #1a1a1a; letter-spacing: 2px; text-transform: uppercase;">Análise Geográfica</p>
                    <div style="margin:0 0 8px 0; font-size:26px; font-weight:800; color:#1a1a1a; line-height:1.2;">Performance por Região</div>
                    <p style="margin: 0; font-size: 14px; color: #666; line-height: 1.6; max-width: 860px;">Cada ponto representa um ensaio individual. A <strong>barra vertical</strong> indica a média por região. Identifique onde cada cultivar performa melhor e como os resultados se distribuem.</p>
                </div>
            """, unsafe_allow_html=True)

            col_geo1, col_geo2 = st.columns([1, 4])
            with col_geo1:
                geo_nivel = st.selectbox(
                    "Agrupar por",
                    options=["Regional", "Estado", "Cidade"],
                    key="grad_geo_nivel"
                )

            col_geo = {"Regional": "regional_nome", "Estado": "estado_nome", "Cidade": "cidade_nome"}[geo_nivel]

            # Pontos individuais
            df_geo_raw = df_plot[df_plot[col_mat].isin(mats_sel)].copy()
            df_geo_raw = df_geo_raw[[col_geo, col_mat, "categoria_material", "resultado_prod_scha_corrigido"]].dropna()

            # Estatísticas para ordenação e marcador de média
            df_geo_stats = df_geo_raw.groupby([col_geo, col_mat, "categoria_material"])["resultado_prod_scha_corrigido"] \
                .agg(n="count", media="mean").reset_index()
            df_geo_stats = df_geo_stats[df_geo_stats["n"] >= 2]

            # Filtra pontos individuais para pares região+material com ao menos 2 ensaios
            pares_validos = set(zip(df_geo_stats[col_geo], df_geo_stats[col_mat]))
            df_geo_raw = df_geo_raw[
                df_geo_raw.apply(lambda r: (r[col_geo], r[col_mat]) in pares_validos, axis=1)
            ]

            if len(df_geo_raw) == 0:
                st.info("Sem dados suficientes para análise geográfica com os filtros selecionados.")
            else:
                stine_geo = df_geo_stats[df_geo_stats["categoria_material"] == "STINE"] \
                    .groupby(col_geo)["media"].mean().sort_values(ascending=True)
                ordem_geo = stine_geo.index.tolist()

                outras = [r for r in df_geo_raw[col_geo].unique() if r not in ordem_geo]
                ordem_geo = outras + ordem_geo

                # Paleta de cores — STINE tons quentes, concorrência tons frios/neutros
                paleta_stine = ["#009D57", "#7ED321", "#00C49A", "#5DB85C", "#A8D500"]
                paleta_conc  = ["#4A90D9", "#7B5EA7", "#D97706", "#DC2626", "#0891B2", "#BE185D", "#92400E"]

                idx_stine = 0
                idx_conc  = 0
                cor_por_mat = {}
                for mat in mats_sel:
                    cat = df_geo_stats[df_geo_stats[col_mat] == mat]["categoria_material"].iloc[0] \
                        if len(df_geo_stats[df_geo_stats[col_mat] == mat]) > 0 else "Concorrência"
                    if cat == "STINE":
                        cor_por_mat[mat] = paleta_stine[idx_stine % len(paleta_stine)]
                        idx_stine += 1
                    else:
                        cor_por_mat[mat] = paleta_conc[idx_conc % len(paleta_conc)]
                        idx_conc += 1

                import numpy as np

                st.markdown("""
                    <div style="display:flex; gap:24px; align-items:center; margin: 4px 0 16px 0; flex-wrap:wrap;">
                        <span style="font-size:12px; font-weight:700; color:#555; text-transform:uppercase; letter-spacing:1px;">Como ler:</span>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <div style="width:10px; height:10px; border-radius:50%; background:rgba(0,100,80,0.45); flex-shrink:0;"></div>
                            <span style="font-size:12px; color:#333;">Ensaio individual</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <div style="width:3px; height:16px; background:rgba(0,100,80,1); border-radius:1px; flex-shrink:0;"></div>
                            <span style="font-size:12px; color:#333;">Média do material na região</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                fig_geo = go.Figure()

                n_mats = len(mats_sel)
                for i, mat in enumerate(mats_sel):
                    df_mat_raw = df_geo_raw[df_geo_raw[col_mat] == mat]
                    if len(df_mat_raw) == 0:
                        continue
                    is_stine = (df_mat_raw["categoria_material"].iloc[0] == "STINE")
                    cor = cor_por_mat[mat]
                    offset = (i - (n_mats - 1) / 2) * 0.22

                    # Média e n geral do material (para legenda)
                    media_geral  = df_mat_raw["resultado_prod_scha_corrigido"].mean()
                    n_geral      = len(df_mat_raw)
                    nome_legenda = f"{mat}  —  {media_geral:.1f} sc/ha (n={n_geral})"

                    # Jitter vertical
                    rng = np.random.default_rng(seed=hash(mat) % (2**32))
                    y_vals = []
                    for r in df_mat_raw[col_geo]:
                        base = ordem_geo.index(r) + offset if r in ordem_geo else offset
                        y_vals.append(base + rng.uniform(-0.15, 0.15))

                    # Pontos individuais com rótulo
                    fig_geo.add_trace(go.Scatter(
                        x=df_mat_raw["resultado_prod_scha_corrigido"],
                        y=y_vals,
                        mode="markers+text",
                        name=nome_legenda,
                        legendgroup=mat,
                        showlegend=True,
                        marker=dict(
                            size=11,
                            color=cor,
                            opacity=0.8,
                            symbol="circle" if is_stine else "diamond",
                            line=dict(color="white", width=1)
                        ),
                        text=df_mat_raw["resultado_prod_scha_corrigido"].apply(lambda v: f"  {v:.1f}"),
                        textposition="middle right",
                        textfont=dict(size=11, color="rgba(0,0,0,0.85)"),
                        customdata=df_mat_raw[[col_geo, "resultado_prod_scha_corrigido"]].values,
                        hovertemplate=(
                            f"<b>{mat}</b><br>"
                            "%{customdata[0]}<br>"
                            "Resultado: <b>%{customdata[1]:.1f} sc/ha</b><extra></extra>"
                        )
                    ))

                    # Linha vertical "|" marcando a média por região
                    df_mat_stats = df_geo_stats[df_geo_stats[col_mat] == mat]
                    for _, srow in df_mat_stats.iterrows():
                        regiao = srow[col_geo]
                        if regiao not in ordem_geo:
                            continue
                        y_mean = ordem_geo.index(regiao) + offset
                        fig_geo.add_shape(
                            type="line",
                            x0=srow["media"], x1=srow["media"],
                            y0=y_mean - 0.22, y1=y_mean + 0.22,
                            xref="x", yref="y",
                            line=dict(color=cor, width=3),
                            layer="above"
                        )

                fig_geo.update_layout(
                    height=max(380, len(ordem_geo) * 44 + 100),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=80, t=10, b=40),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom", y=1.02,
                        font=dict(color="black", size=11)
                    ),
                    xaxis=dict(
                        title=dict(text="<b>sc/ha</b>", font=dict(color="black", size=14)),
                        tickfont=dict(color="black", size=13, family="Arial Black"),
                        tickcolor="black",
                        showgrid=True,
                        gridcolor="rgba(0,0,0,0.06)",
                        zeroline=False,
                    ),
                    yaxis=dict(
                        tickfont=dict(color="black", size=13, family="Arial Black"),
                        tickcolor="black",
                        showgrid=True,
                        gridcolor="rgba(0,0,0,0.08)",
                        zeroline=False,
                        tickmode="array",
                        tickvals=list(range(len(ordem_geo))),
                        ticktext=ordem_geo,
                        range=[-0.6, len(ordem_geo) - 0.4],
                    ),
                    font=dict(color="black"),
                )
                st.plotly_chart(fig_geo, use_container_width=True)