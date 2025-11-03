import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# Configuración de la página
st.set_page_config(
    page_title="Pronóstico Financiero - Estado de Resultados",
    page_icon="📊",
    layout="wide"
)

# CSS personalizado para mejorar la apariencia
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .scenario-optimista {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 10px;
        margin: 5px 0;
    }
    .scenario-realista {
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 10px;
        margin: 5px 0;
    }
    .scenario-pesimista {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 10px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📈 Pronóstico Financiero </div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Estado de Resultados Proyectado a 12 meses con análisis de escenarios</div>', unsafe_allow_html=True)

# ==========================
# Barra lateral: Inputs del usuario
# ==========================
st.sidebar.header("🔧 Configuración de supuestos")

# NUEVO: Selector de escenarios
st.sidebar.subheader("🎭 Análisis de Escenarios")
modo_escenarios = st.sidebar.checkbox("Activar análisis de escenarios", value=False)

if modo_escenarios:
    st.sidebar.info("📊 Se generarán 3 escenarios: Optimista, Realista y Pesimista")
    
    # Configuración de variaciones para escenarios
    st.sidebar.markdown("**Configuración de variaciones:**")
    variacion_optimista = st.sidebar.slider("Variación optimista (%)", 5.0, 50.0, 20.0, 5.0)
    variacion_pesimista = st.sidebar.slider("Variación pesimista (%)", -50.0, -5.0, -20.0, 5.0)

# Sección 1: Ventas
st.sidebar.subheader("💰 Proyección de Ventas")

# 👇 DEFINIR meses_nombres AL INICIO
meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

ventas_base = st.sidebar.number_input("Ventas del primer mes ($)", min_value=0.0, value=50000.0, step=1000.0)
crecimiento_ventas = st.sidebar.slider("Crecimiento mensual de ventas (%)", -20.0, 50.0, 3.0, 0.5) / 100

# Nueva opción: Estacionalidad
usar_estacionalidad = st.sidebar.checkbox("Aplicar factores de estacionalidad", value=False)
factores_estacionalidad = {}
if usar_estacionalidad:
    st.sidebar.markdown("**Ajusta por mes (1.0 = normal):**")
    cols = st.sidebar.columns(3)
    for i, mes in enumerate(meses_nombres):
        with cols[i % 3]:
            factores_estacionalidad[mes] = st.number_input(
                mes, min_value=0.1, max_value=3.0, value=1.0, step=0.1, key=f"est_{mes}"
            )

st.sidebar.markdown("---")

# Sección 2: Costos y Gastos
st.sidebar.subheader("💸 Estructura de Costos")
costo_venta_pct = st.sidebar.slider("% Costo de ventas", 0.0, 100.0, 60.0, 1.0)
gastos_operativos = st.sidebar.number_input("Gastos operativos mensuales ($)", min_value=0.0, value=20000.0, step=500.0)
gastos_financieros = st.sidebar.number_input("Gastos financieros mensuales ($)", min_value=0.0, value=1000.0, step=100.0)
tasa_impuestos = st.sidebar.slider("Tasa de impuestos (%)", 0.0, 100.0, 25.0, 1.0)

# Sección 3: Eventos especiales
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Eventos Especiales")
usar_eventos = st.sidebar.checkbox("Agregar eventos especiales", value=False)
eventos = {}
if usar_eventos:
    num_eventos = st.sidebar.number_input("Número de eventos", min_value=1, max_value=5, value=1)
    for i in range(num_eventos):
        with st.sidebar.expander(f"Evento {i+1}"):
            mes_evento = st.selectbox(f"Mes del evento {i+1}", meses_nombres, key=f"mes_ev_{i}")
            impacto_ventas = st.slider(f"Impacto en ventas (%)", -50.0, 100.0, 0.0, 5.0, key=f"imp_ev_{i}")
            eventos[mes_evento] = eventos.get(mes_evento, 0) + (impacto_ventas / 100)

# ==========================
# Subir datos reales
# ==========================
st.sidebar.markdown("---")
st.sidebar.subheader("📂 Comparar con real (opcional)")
archivo_real = st.sidebar.file_uploader(
    "Sube un archivo Excel con datos reales",
    type=["xlsx"],
    help="El archivo debe tener columnas: Mes, Ventas, Costo de ventas, Gastos operativos, Gastos financieros"
)

df_real = None
if archivo_real is not None:
    try:
        df_real = pd.read_excel(archivo_real)
        required_cols = ["Mes", "Ventas", "Costo de ventas", "Gastos operativos", "Gastos financieros"]
        if not all(col in df_real.columns for col in required_cols):
            st.sidebar.error("❌ Faltan columnas requeridas.")
            df_real = None
        else:
            for col in ["Ventas", "Costo de ventas", "Gastos operativos", "Gastos financieros"]:
                df_real[col] = pd.to_numeric(df_real[col], errors='coerce')
            df_real["Utilidad bruta"] = df_real["Ventas"] - df_real["Costo de ventas"]
            df_real["EBIT"] = df_real["Utilidad bruta"] - df_real["Gastos operativos"]
            df_real["Utilidad antes de impuestos"] = df_real["EBIT"] - df_real["Gastos financieros"]
            df_real["Impuestos"] = df_real["Utilidad antes de impuestos"].apply(lambda x: max(0, x)) * (tasa_impuestos / 100)
            df_real["Utilidad neta"] = df_real["Utilidad antes de impuestos"] - df_real["Impuestos"]
            st.sidebar.success("✅ Datos reales cargados correctamente")
    except Exception as e:
        st.sidebar.error(f"❌ Error al leer el archivo: {e}")
        df_real = None

# ==========================
# Función para calcular proyección
# ==========================
def calcular_proyeccion(ventas_base, crecimiento, multiplicador=1.0):
    """Calcula la proyección con un multiplicador para escenarios"""
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    ventas, costo_venta, utilidad_bruta, ebit, utilidad_antes_imp, impuestos, utilidad_neta = [], [], [], [], [], [], []

    # Ajustar crecimiento según el escenario
    crecimiento_ajustado = crecimiento * multiplicador
    
    for t, mes in enumerate(meses):
        # Crecimiento base
        venta_mes = ventas_base * ((1 + crecimiento_ajustado) ** t)
        
        # Aplicar estacionalidad
        if usar_estacionalidad and mes in factores_estacionalidad:
            venta_mes *= factores_estacionalidad[mes]
        
        # Aplicar eventos especiales
        if usar_eventos and mes in eventos:
            venta_mes *= (1 + eventos[mes])
        
        cv = venta_mes * (costo_venta_pct / 100)
        ub = venta_mes - cv
        ebit_mes = ub - gastos_operativos
        uai = ebit_mes - gastos_financieros
        imp = max(0, uai) * (tasa_impuestos / 100)
        un = uai - imp

        ventas.append(venta_mes)
        costo_venta.append(cv)
        utilidad_bruta.append(ub)
        ebit.append(ebit_mes)
        utilidad_antes_imp.append(uai)
        impuestos.append(imp)
        utilidad_neta.append(un)

    df = pd.DataFrame({
        "Mes": meses,
        "Ventas": ventas,
        "Costo de ventas": costo_venta,
        "Utilidad bruta": utilidad_bruta,
        "Gastos operativos": [gastos_operativos] * 12,
        "EBIT": ebit,
        "Gastos financieros": [gastos_financieros] * 12,
        "Utilidad antes de impuestos": utilidad_antes_imp,
        "Impuestos": impuestos,
        "Utilidad neta": utilidad_neta
    })
    
    return df

# ==========================
# Cálculos: Proyección (12 meses)
# ==========================
if modo_escenarios:
    # Calcular los 3 escenarios
    df_realista = calcular_proyeccion(ventas_base, crecimiento_ventas, 1.0)
    df_optimista = calcular_proyeccion(ventas_base, crecimiento_ventas, 1 + (variacion_optimista/100))
    df_pesimista = calcular_proyeccion(ventas_base, crecimiento_ventas, 1 + (variacion_pesimista/100))
    
    # Por defecto mostramos el realista
    df_proy = df_realista
else:
    # Solo calcular escenario base
    df_proy = calcular_proyeccion(ventas_base, crecimiento_ventas, 1.0)

# ==========================
# Métricas clave mejoradas
# ==========================
st.subheader("📊 Indicadores Clave de Rendimiento (KPIs)")

if modo_escenarios:
    # Mostrar comparación de escenarios
    st.markdown("### 🎭 Comparación de Escenarios")
    
    col1, col2, col3 = st.columns(3)
    
    # Escenario Optimista
    with col1:
        st.markdown('<div class="scenario-optimista"><b>🚀 ESCENARIO OPTIMISTA</b></div>', unsafe_allow_html=True)
        utilidad_opt = df_optimista["Utilidad neta"].sum()
        ventas_opt = df_optimista["Ventas"].sum()
        margen_opt = (utilidad_opt / ventas_opt * 100) if ventas_opt > 0 else 0
        st.metric("Utilidad neta (12m)", f"${utilidad_opt:,.0f}", delta=f"+{variacion_optimista}%")
        st.metric("Ventas totales", f"${ventas_opt:,.0f}")
        st.metric("Margen neto", f"{margen_opt:.1f}%")
    
    # Escenario Realista
    with col2:
        st.markdown('<div class="scenario-realista"><b>🎯 ESCENARIO REALISTA</b></div>', unsafe_allow_html=True)
        utilidad_real = df_realista["Utilidad neta"].sum()
        ventas_real = df_realista["Ventas"].sum()
        margen_real = (utilidad_real / ventas_real * 100) if ventas_real > 0 else 0
        st.metric("Utilidad neta (12m)", f"${utilidad_real:,.0f}")
        st.metric("Ventas totales", f"${ventas_real:,.0f}")
        st.metric("Margen neto", f"{margen_real:.1f}%")
    
    # Escenario Pesimista
    with col3:
        st.markdown('<div class="scenario-pesimista"><b>⚠️ ESCENARIO PESIMISTA</b></div>', unsafe_allow_html=True)
        utilidad_pes = df_pesimista["Utilidad neta"].sum()
        ventas_pes = df_pesimista["Ventas"].sum()
        margen_pes = (utilidad_pes / ventas_pes * 100) if ventas_pes > 0 else 0
        st.metric("Utilidad neta (12m)", f"${utilidad_pes:,.0f}", delta=f"{variacion_pesimista}%")
        st.metric("Ventas totales", f"${ventas_pes:,.0f}")
        st.metric("Margen neto", f"{margen_pes:.1f}%")

else:
    # Mostrar métricas normales
    col1, col2, col3, col4 = st.columns(4)

    total_utilidad_neta = df_proy["Utilidad neta"].sum()
    total_ventas = df_proy["Ventas"].sum()
    margen_neto_prom = (total_utilidad_neta / total_ventas) * 100 if total_ventas > 0 else 0
    margen_bruto_prom = (df_proy["Utilidad bruta"].sum() / total_ventas) * 100 if total_ventas > 0 else 0

    col1.metric("💵 Ventas totales (12m)", f"${total_ventas:,.0f}", 
                delta=f"{crecimiento_ventas*100:.1f}% mensual")
    col2.metric("💰 Utilidad neta (12m)", f"${total_utilidad_neta:,.0f}",
                delta=f"{margen_neto_prom:.1f}% margen")
    col3.metric("📈 Margen bruto", f"{margen_bruto_prom:.1f}%")
    col4.metric("📉 EBIT promedio", f"${df_proy['EBIT'].mean():,.0f}")

# ==========================
# Gráfico principal mejorado
# ==========================
st.markdown("---")
st.subheader("📊 Análisis Visual de Rentabilidad")

# Crear tabs para diferentes visualizaciones
if modo_escenarios:
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Comparación Escenarios", "💹 Desglose Financiero", "🎯 Márgenes", "📊 Rango de Resultados"])
else:
    tab1, tab2, tab3 = st.tabs(["📈 Utilidad Neta", "💹 Desglose Financiero", "🎯 Márgenes"])

with tab1:
    if modo_escenarios:
        # Gráfico comparando los 3 escenarios
        fig1 = go.Figure()
        
        # Escenario Optimista
        fig1.add_trace(go.Scatter(
            x=df_optimista["Mes"],
            y=df_optimista["Utilidad neta"],
            mode='lines+markers',
            name='Optimista',
            line=dict(color='#28a745', width=3),
            marker=dict(size=8, symbol='circle')
        ))
        
        # Escenario Realista
        fig1.add_trace(go.Scatter(
            x=df_realista["Mes"],
            y=df_realista["Utilidad neta"],
            mode='lines+markers',
            name='Realista',
            line=dict(color='#17a2b8', width=3),
            marker=dict(size=8, symbol='square')
        ))
        
        # Escenario Pesimista
        fig1.add_trace(go.Scatter(
            x=df_pesimista["Mes"],
            y=df_pesimista["Utilidad neta"],
            mode='lines+markers',
            name='Pesimista',
            line=dict(color='#dc3545', width=3),
            marker=dict(size=8, symbol='diamond')
        ))
        
        # Agregar banda de incertidumbre
        fig1.add_trace(go.Scatter(
            x=df_optimista["Mes"].tolist() + df_pesimista["Mes"].tolist()[::-1],
            y=df_optimista["Utilidad neta"].tolist() + df_pesimista["Utilidad neta"].tolist()[::-1],
            fill='toself',
            fillcolor='rgba(128,128,128,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            showlegend=True,
            name='Rango de variación'
        ))
        
        fig1.update_layout(
            title="Utilidad Neta Mensual: Análisis de Escenarios",
            xaxis_title="Mes",
            yaxis_title="Utilidad Neta ($)",
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
    else:
        # Gráfico de líneas mejorado (versión normal)
        fig1 = go.Figure()
        
        # Línea proyectada
        fig1.add_trace(go.Scatter(
            x=df_proy["Mes"],
            y=df_proy["Utilidad neta"],
            mode='lines+markers',
            name='Proyectado',
            line=dict(color='#00cc96', width=3),
            marker=dict(size=10, symbol='circle'),
            fill='tozeroy',
            fillcolor='rgba(0, 204, 150, 0.1)'
        ))
        
        # Si hay datos reales, agregarlos
        if df_real is not None:
            fig1.add_trace(go.Scatter(
                x=df_real["Mes"],
                y=df_real["Utilidad neta"],
                mode='lines+markers',
                name='Real',
                line=dict(color='#ef553b', width=3, dash='dash'),
                marker=dict(size=10, symbol='square')
            ))
        
        fig1.update_layout(
            title="Utilidad Neta Mensual: Proyección vs Real",
            xaxis_title="Mes",
            yaxis_title="Utilidad Neta ($)",
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
    
    fig1.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig1.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    
    st.plotly_chart(fig1, config={}, use_container_width=True, key="chart1")

    #st.plotly_chart(fig1, width="stretch", key="chart1")
    
    # Botón para exportar gráfico
    try:
        img_bytes = fig1.to_image(format="png", width=1200, height=600, scale=2)
        st.download_button(
            label="📸 Descargar gráfico como imagen PNG",
            data=img_bytes,
            file_name="utilidad_neta_proyeccion.png",
            mime="image/png"
        )
    except:
        st.info("💡 Instala 'kaleido' para exportar gráficos: pip install kaleido")

with tab2:
    # Gráfico de cascada/barras apiladas
    fig2 = go.Figure()
    
    df_display = df_realista if modo_escenarios else df_proy
    
    fig2.add_trace(go.Bar(
        x=df_display["Mes"],
        y=df_display["Ventas"],
        name='Ventas',
        marker_color='lightblue'
    ))
    
    fig2.add_trace(go.Bar(
        x=df_display["Mes"],
        y=df_display["Costo de ventas"],
        name='Costo de ventas',
        marker_color='lightcoral'
    ))
    
    fig2.add_trace(go.Bar(
        x=df_display["Mes"],
        y=df_display["Gastos operativos"],
        name='Gastos operativos',
        marker_color='lightsalmon'
    ))
    
    fig2.add_trace(go.Scatter(
        x=df_display["Mes"],
        y=df_display["Utilidad neta"],
        name='Utilidad neta',
        mode='lines+markers',
        line=dict(color='green', width=3),
        marker=dict(size=10)
    ))
    
    fig2.update_layout(
        title="Desglose de Ingresos y Gastos",
        xaxis_title="Mes",
        yaxis_title="Monto ($)",
        barmode='group',
        hovermode='x unified',
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    #st.plotly_chart(fig2, width="stretch", key="chart2")
    st.plotly_chart(fig2, config={}, use_container_width=True, key="chart2")
    
    # Botón para exportar gráfico
    try:
        img_bytes = fig2.to_image(format="png", width=1200, height=600, scale=2)
        st.download_button(
            label="📸 Descargar gráfico como imagen PNG",
            data=img_bytes,
            file_name="desglose_financiero.png",
            mime="image/png",
            key="download2"
        )
    except:
        pass

with tab3:
    # Gráfico de márgenes
    df_display = df_realista if modo_escenarios else df_proy
    df_display["Margen bruto (%)"] = (df_display["Utilidad bruta"] / df_display["Ventas"]) * 100
    df_display["Margen neto (%)"] = (df_display["Utilidad neta"] / df_display["Ventas"]) * 100
    
    fig3 = go.Figure()
    
    fig3.add_trace(go.Scatter(
        x=df_display["Mes"],
        y=df_display["Margen bruto (%)"],
        mode='lines+markers',
        name='Margen Bruto',
        line=dict(color='#636efa', width=2),
        fill='tozeroy'
    ))
    
    fig3.add_trace(go.Scatter(
        x=df_display["Mes"],
        y=df_display["Margen neto (%)"],
        mode='lines+markers',
        name='Margen Neto',
        line=dict(color='#00cc96', width=2),
        fill='tozeroy'
    ))
    
    fig3.update_layout(
        title="Evolución de Márgenes de Rentabilidad",
        xaxis_title="Mes",
        yaxis_title="Margen (%)",
        hovermode='x unified',
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    #st.plotly_chart(fig3, width="stretch", key="chart3")
    st.plotly_chart(fig3, config={}, use_container_width=True, key="chart3")
    
    # Botón para exportar gráfico
    try:
        img_bytes = fig3.to_image(format="png", width=1200, height=600, scale=2)
        st.download_button(
            label="📸 Descargar gráfico como imagen PNG",
            data=img_bytes,
            file_name="margenes_rentabilidad.png",
            mime="image/png",
            key="download3"
        )
    except:
        pass

# Tab adicional solo para modo escenarios
if modo_escenarios:
    with tab4:
        # Gráfico de caja (box plot) mostrando rango de resultados
        fig4 = go.Figure()
        
        meses = df_realista["Mes"].tolist()
        
        for i, mes in enumerate(meses):
            valores = [
                df_pesimista.iloc[i]["Utilidad neta"],
                df_realista.iloc[i]["Utilidad neta"],
                df_optimista.iloc[i]["Utilidad neta"]
            ]
            
            fig4.add_trace(go.Box(
                y=valores,
                name=mes,
                marker_color='lightblue',
                boxmean='sd'
            ))
        
        fig4.update_layout(
            title="Rango de Utilidad Neta por Mes según Escenarios",
            xaxis_title="Mes",
            yaxis_title="Utilidad Neta ($)",
            height=500,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        #st.plotly_chart(fig4, width="stretch", key="chart4")
        st.plotly_chart(fig4, config={}, use_container_width=True, key="chart4")

        
        # Botón para exportar gráfico
        try:
            img_bytes = fig4.to_image(format="png", width=1200, height=600, scale=2)
            st.download_button(
                label="📸 Descargar gráfico como imagen PNG",
                data=img_bytes,
                file_name="rango_escenarios.png",
                mime="image/png",
                key="download4"
            )
        except:
            pass

# ==========================
# Tabla de resultados mejorada
# ==========================
st.markdown("---")
st.subheader("📋 Estado de Resultados Detallado")

# Selector de escenario para la tabla (si está activado el modo)
if modo_escenarios:
    escenario_tabla = st.radio(
        "Selecciona el escenario para ver en detalle:",
        ["Realista", "Optimista", "Pesimista"],
        horizontal=True
    )
    
    if escenario_tabla == "Optimista":
        df_display_tabla = df_optimista
    elif escenario_tabla == "Pesimista":
        df_display_tabla = df_pesimista
    else:
        df_display_tabla = df_realista
else:
    df_display_tabla = df_proy

def safe_format(val):
    if pd.isna(val):
        return ""
    try:
        return f"${float(val):,.0f}"
    except (ValueError, TypeError):
        return str(val)

def format_percentage(val):
    if pd.isna(val):
        return ""
    try:
        return f"{float(val):.1f}%"
    except (ValueError, TypeError):
        return str(val)

# Calcular márgenes para la tabla
df_display_tabla["Margen bruto (%)"] = (df_display_tabla["Utilidad bruta"] / df_display_tabla["Ventas"]) * 100
df_display_tabla["Margen neto (%)"] = (df_display_tabla["Utilidad neta"] / df_display_tabla["Ventas"]) * 100

# Mostrar tabla completa con formato
df_tabla = df_display_tabla.copy()
df_tabla = df_tabla.set_index("Mes")

# Aplicar formato condicional
st.dataframe(
    df_tabla.style.format({
        "Ventas": safe_format,
        "Costo de ventas": safe_format,
        "Utilidad bruta": safe_format,
        "Gastos operativos": safe_format,
        "EBIT": safe_format,
        "Gastos financieros": safe_format,
        "Utilidad antes de impuestos": safe_format,
        "Impuestos": safe_format,
        "Utilidad neta": safe_format,
        "Margen bruto (%)": format_percentage,
        "Margen neto (%)": format_percentage
    }).background_gradient(subset=["Utilidad neta"], cmap="RdYlGn"),
    width="stretch"
)

# ==========================
# Análisis adicional
# ==========================
st.markdown("---")
st.subheader("🔍 Análisis de Sensibilidad")

if modo_escenarios:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📊 Resumen Optimista:**")
        mejor_mes_opt = df_optimista.loc[df_optimista["Utilidad neta"].idxmax()]
        st.success(f"Mejor mes: **{mejor_mes_opt['Mes']}**")
        st.metric("Utilidad máxima", f"${mejor_mes_opt['Utilidad neta']:,.0f}")
    
    with col2:
        st.markdown("**📊 Resumen Realista:**")
        mejor_mes_real = df_realista.loc[df_realista["Utilidad neta"].idxmax()]
        st.info(f"Mejor mes: **{mejor_mes_real['Mes']}**")
        st.metric("Utilidad máxima", f"${mejor_mes_real['Utilidad neta']:,.0f}")
    
    with col3:
        st.markdown("**📊 Resumen Pesimista:**")
        peor_mes_pes = df_pesimista.loc[df_pesimista["Utilidad neta"].idxmin()]
        if peor_mes_pes['Utilidad neta'] < 0:
            st.error(f"Riesgo en: **{peor_mes_pes['Mes']}**")
            st.metric("Pérdida potencial", f"${peor_mes_pes['Utilidad neta']:,.0f}")
        else:
            st.warning(f"Mes más bajo: **{peor_mes_pes['Mes']}**")
            st.metric("Utilidad mínima", f"${peor_mes_pes['Utilidad neta']:,.0f}")
    
    # Análisis de probabilidad
    st.markdown("---")
    st.markdown("### 🎲 Análisis de Probabilidad")
    
    utilidad_opt_total = df_optimista["Utilidad neta"].sum()
    utilidad_real_total = df_realista["Utilidad neta"].sum()
    utilidad_pes_total = df_pesimista["Utilidad neta"].sum()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Rango de utilidad neta anual:**")
        st.write(f"- 🟢 Mejor caso: **${utilidad_opt_total:,.0f}**")
        st.write(f"- 🔵 Caso esperado: **${utilidad_real_total:,.0f}**")
        st.write(f"- 🔴 Peor caso: **${utilidad_pes_total:,.0f}**")
        
        diferencia = utilidad_opt_total - utilidad_pes_total
        st.write(f"- 📊 Rango de variación: **${diferencia:,.0f}**")
    
    with col2:
        # Gráfico de tornado para mostrar sensibilidad
        fig_tornado = go.Figure()
        
        categorias = ['Utilidad Neta']
        
        fig_tornado.add_trace(go.Bar(
            y=categorias,
            x=[utilidad_real_total - utilidad_pes_total],
            name='Riesgo a la baja',
            orientation='h',
            marker=dict(color='#dc3545'),
            base=utilidad_pes_total
        ))
        
        fig_tornado.add_trace(go.Bar(
            y=categorias,
            x=[utilidad_opt_total - utilidad_real_total],
            name='Potencial al alza',
            orientation='h',
            marker=dict(color='#28a745'),
            base=utilidad_real_total
        ))
        
        fig_tornado.update_layout(
            title="Diagrama de Sensibilidad - Utilidad Anual",
            xaxis_title="Utilidad Neta ($)",
            barmode='stack',
            height=250,
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        #st.plotly_chart(fig_tornado, width="stretch", key="tornado")
        st.plotly_chart(fig_tornado, config={}, use_container_width=True, key="tornado")


else:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Mejor mes proyectado:**")
        mejor_mes = df_proy.loc[df_proy["Utilidad neta"].idxmax()]
        st.info(f"**{mejor_mes['Mes']}** con ${mejor_mes['Utilidad neta']:,.0f} de utilidad neta")

    with col2:
        st.markdown("**Mes más desafiante:**")
        peor_mes = df_proy.loc[df_proy["Utilidad neta"].idxmin()]
        if peor_mes['Utilidad neta'] < 0:
            st.error(f"**{peor_mes['Mes']}** con pérdida de ${abs(peor_mes['Utilidad neta']):,.0f}")
        else:
            st.warning(f"**{peor_mes['Mes']}** con ${peor_mes['Utilidad neta']:,.0f} de utilidad neta")

# ==========================
# Descargar como Excel
# ==========================
st.markdown("---")
st.subheader("📥 Exportar Resultados")

@st.cache_data
def to_excel(proy, real=None, escenarios=None):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if escenarios:
            escenarios['optimista'].to_excel(writer, sheet_name="Escenario Optimista", index=False)
            escenarios['realista'].to_excel(writer, sheet_name="Escenario Realista", index=False)
            escenarios['pesimista'].to_excel(writer, sheet_name="Escenario Pesimista", index=False)
        else:
            proy.to_excel(writer, sheet_name="Proyección", index=False)
        
        if real is not None:
            real.to_excel(writer, sheet_name="Datos reales", index=False)
    return output.getvalue()

if modo_escenarios:
    escenarios_dict = {
        'optimista': df_optimista,
        'realista': df_realista,
        'pesimista': df_pesimista
    }
    excel_data = to_excel(None, df_real, escenarios_dict)
else:
    excel_data = to_excel(df_proy, df_real)

col1, col2 = st.columns(2)

with col1:
    st.download_button(
        label="📥 Descargar resultados como Excel (.xlsx)",
        data=excel_data,
        file_name="pronostico_financiero_completo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

with col2:
    if modo_escenarios:
        st.info("📊 El archivo incluye los 3 escenarios en hojas separadas")
    else:
        st.info("📊 El archivo incluye la proyección completa")

# ==========================
# Instrucciones
# ==========================
st.markdown("---")
with st.expander("ℹ️ ¿Cómo usar esta herramienta?"):
    st.markdown("""
    ### 📖 Guía de uso
    
    **1. Configuración básica:**
    - Ajusta las ventas del primer mes y el crecimiento esperado
    - Define tu estructura de costos (% de costo de ventas)
    - Configura gastos operativos y financieros
    
    **2. Funciones avanzadas:**
    - **Estacionalidad**: Activa esta opción si tu negocio tiene variaciones estacionales (ej: retail en diciembre)
    - **Eventos especiales**: Agrega promociones, campañas o eventos que impacten ventas en meses específicos
    - **🎭 Análisis de escenarios**: Activa para ver proyecciones optimistas, realistas y pesimistas simultáneamente
    
    **3. Análisis de escenarios:**
    - El **escenario optimista** aplica un crecimiento acelerado (configurable)
    - El **escenario realista** usa tus supuestos base
    - El **escenario pesimista** modela un crecimiento reducido o negativo
    - Útil para: planificación estratégica, análisis de riesgos, presentaciones a inversionistas
    
    **4. Exportar gráficos:**
    - Cada gráfico tiene un botón "📸 Descargar gráfico como imagen PNG"
    - Las imágenes son de alta resolución (1200x600px)
    - Perfectas para presentaciones, reportes e informes ejecutivos
    - **Nota**: Requiere la librería `kaleido` instalada (`pip install kaleido`)
    
    **5. Comparación con datos reales:**
    - Sube un archivo Excel con datos reales para comparar tu proyección
    - El archivo debe tener estas columnas: Mes, Ventas, Costo de ventas, Gastos operativos, Gastos financieros
    
    **6. Análisis:**
    - Revisa los KPIs principales en la parte superior
    - Explora los diferentes gráficos en las pestañas
    - Identifica los meses más rentables y los desafiantes
    - En modo escenarios, analiza el rango de variación y los riesgos potenciales
    
    ### 📊 Formato del archivo de datos reales
    
    | Mes | Ventas | Costo de ventas | Gastos operativos | Gastos financieros |
    |-----|--------|-----------------|-------------------|---------------------|
    | Ene | 48000  | 28800          | 19000            | 950                |
    | Feb | 52000  | 31200          | 19500            | 950                |
    
    - **Mes**: Ene, Feb, Mar, Abr, May, Jun, Jul, Ago, Sep, Oct, Nov, Dic
    - **Valores**: Solo números (sin símbolos $, comas ni texto)
    
    ### 💡 Casos de uso recomendados
    
    - **Planificación anual**: Usa el escenario realista como base para tu presupuesto
    - **Análisis de riesgos**: Revisa el escenario pesimista para preparar planes de contingencia
    - **Presentación a inversionistas**: Muestra los 3 escenarios para demostrar comprensión del negocio
    - **Seguimiento mensual**: Compara con datos reales y ajusta supuestos
    
    ### 🎓 Interpretación de resultados
    
    - **Margen bruto > 40%**: Excelente poder de fijación de precios
    - **Margen neto > 15%**: Operación eficiente y rentable
    - **EBIT positivo**: La operación genera valor antes de financiamiento
    - **Utilidad neta negativa**: Revisar estructura de costos o estrategia de precios
    """)

with st.expander("🔧 Solución de problemas"):
    st.markdown("""
    ### Exportación de gráficos no funciona
    
    Si ves el mensaje "Instala 'kaleido' para exportar gráficos", ejecuta:
    
    ```bash
    pip install kaleido
    ```
    
    O si usas entorno virtual:
    
    ```bash
    .venv\\Scripts\\activate  # Windows
    source .venv/bin/activate  # Mac/Linux
    pip install kaleido
    ```
    
    Luego reinicia el servidor de Streamlit:
    ```bash
    streamlit run app.py
    ```
    
    ### Otros problemas comunes
    
    - **Gráficos no se muestran**: Verifica que tengas instalado `plotly` actualizado
    - **Archivo Excel no carga**: Asegúrate que las columnas coincidan exactamente con los nombres requeridos
    - **Números extraños**: Revisa que los datos no contengan texto o símbolos
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><b>📊 Herramienta de Pronóstico Financiero</b></p>
    <p>Desarrollada para análisis de rentabilidad y planificación estratégica</p>
    <p style='font-size: 0.8em;'>💡 Tip: Ajusta los supuestos en tiempo real y observa el impacto inmediato en tus proyecciones</p>
</div>
""", unsafe_allow_html=True)