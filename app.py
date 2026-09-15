import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import urllib.parse
import requests

# 1. Configuración de página
st.set_page_config(page_title="BapSync - Turnos BAPES", page_icon="🛡️", layout="centered")

# Estilos visuales
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #0c5c3c;
        color: white;
        font-weight: bold;
        border-radius: 10px;
        padding: 12px;
        font-size: 16px;
    }
    .stButton>button:hover {
        background-color: #08432b;
        color: white;
    }
    .banner-card {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 15px;
        text-align: center;
        color: #14532d;
    }
    </style>
""", unsafe_allow_html=True)

# URL DE LA API DE GOOGLE SHEETS
API_URL = st.secrets.get("SHEET_API_URL", "")

def cargar_turnos():
    if not API_URL:
        return pd.DataFrame()
    try:
        res = requests.get(API_URL, timeout=12, allow_redirects=True)
        if res.status_code == 200:
            datos = res.json()
            if isinstance(datos, list) and len(datos) > 0:
                return pd.DataFrame(datos)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# 2. Logo institucional
col_izq, col_centro, col_der = st.columns([1, 4, 1])
with col_centro:
    try:
        st.image("logo_bapsync.png", use_container_width=True)
    except Exception:
        st.markdown("<h2 style='text-align: center; color: #0c5c3c;'>🛡️ BapSync</h2>", unsafe_allow_html=True)

# 3. Lógica mensual dinámica (Se renueva automáticamente el 1 de cada mes)
hoy = datetime.today()
meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

mes_actual_nombre = meses_nombres[hoy.month - 1]
total_dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]

st.markdown(f"<div class='banner-card'><b>Seguridad Escolar BAPES — Mes de {mes_actual_nombre} {hoy.year}</b><br>Turnos: Mañana (7:30 - 8:15) y Tarde (2:15 - 3:00) | Máx. 5 padres por turno</div>", unsafe_allow_html=True)

# Generar todos los lunes a viernes del mes
dias_mes_dict = {}
for dia_num in range(1, total_dias_mes + 1):
    fecha_obj = datetime(hoy.year, hoy.month, dia_num)
    if fecha_obj.weekday() < 5:  # Lunes a Viernes
        nombre_d = dias_nombres[fecha_obj.weekday()]
        etiqueta = f"{nombre_d} {dia_num:02d} de {mes_actual_nombre}"
        dias_mes_dict[etiqueta] = {
            "fecha_str": fecha_obj.strftime("%Y-%m-%d"),
            "dia": nombre_d,
            "dia_num": dia_num
        }

df_turnos = cargar_turnos()

# 4. Pestañas principales
tab_registro, tab_horario = st.tabs(["📝 Inscribirme a un Turno", "📅 Ver Rol Mensual"])

with tab_registro:
    st.markdown(f"#### Selecciona tu fecha en {mes_actual_nombre} y turno:")
    
    dia_elegido_label = st.selectbox("📅 Día de asistencia (Lunes a Viernes):", list(dias_mes_dict.keys()))
    info_dia = dias_mes_dict[dia_elegido_label]
    
    turnos_disponibles = [
        "🌅 Mañana: 07:30 a 08:15 (Entrada)",
        "🌇 Tarde: 02:15 a 03:00 (Salida)"
    ]
    turno_elegido = st.radio("⏰ Turno:", turnos_disponibles)

    # Validar cupos en tiempo real para ese día y turno
    if not df_turnos.empty and "fecha" in df_turnos.columns and "turno" in df_turnos.columns:
        fechas_col = df_turnos["fecha"].astype(str).str.strip().str[:10]
        turnos_col = df_turnos["turno"].astype(str).str.strip()
        
        ocupados = len(df_turnos[
            (fechas_col == info_dia["fecha_str"]) & 
            (turnos_col == turno_elegido)
        ])
    else:
        ocupados = 0

    libres = 5 - ocupados

    if libres > 0:
        st.info(f"✅ Cupos disponibles: **{libres} de 5** para el {dia_elegido_label}")
    else:
        st.error(f"❌ Turno completo (5/5 padres registrados). Elige otro día u horario.")

    st.markdown("##### Tus Datos:")
    nombre_padre = st.text_input("Nombre y Apellidos del Apoderado:")
    telefono_padre = st.text_input("Número de Celular / WhatsApp:", max_chars=9)
    estudiante = st.text_input("Nombre del Estudiante:")
    grado = st.text_input("Grado y Sección:")

    if st.button("Confirmar mi Turno en BAPES"):
        if not (nombre_padre and telefono_padre and estudiante):
            st.warning("⚠️ Por favor completa tu nombre, celular y nombre del estudiante.")
        elif libres <= 0:
            st.error("Lo sentimos, este turno ya está completo.")
        elif not API_URL:
            st.error("Falta configurar la URL de la base de datos en los Secrets.")
        else:
            payload = {
                "fecha": info_dia["fecha_str"],
                "dia": info_dia["dia"],
                "turno": turno_elegido,
                "padre": nombre_padre.strip(),
                "telefono": telefono_padre.strip(),
                "estudiante": estudiante.strip(),
                "grado": grado.strip(),
                "creado": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            try:
                r = requests.post(API_URL, json=payload, timeout=15, allow_redirects=True)
                
                if r.status_code in [200, 302] or "ok" in r.text:
                    st.success("🎉 ¡Tu turno ha sido registrado correctamente!")
                    mensaje_wa = f"Hola {nombre_padre}, confirmaste tu turno en BAPES para el {dia_elegido_label} en el horario {turno_elegido}. ¡Gracias por apoyar en la seguridad escolar!"
                    url_whatsapp = f"https://wa.me/51{telefono_padre}?text={urllib.parse.quote(mensaje_wa)}"
                    
                    st.markdown(f"""
                        <div style='text-align: center; margin-top: 10px;'>
                            <a href='{url_whatsapp}' target='_blank' style='background-color:#25D366; color:white; padding:10px 18px; border-radius:8px; text-decoration:none; font-weight:bold; display:inline-block;'>
                                📲 Enviar recordatorio a mi WhatsApp
                            </a>
                        </div>
                    """, unsafe_allow_html=True)
                    st.rerun()
                else:
                    st.error(f"Error al guardar: Código {r.status_code}")
            except Exception as ex:
                st.error(f"Error de conexión: {ex}")

with tab_horario:
    st.markdown(f"#### 📋 Rol de Vigilancia BAPES ({mes_actual_nombre} {hoy.year})")
    
    col_ref, col_link = st.columns([1, 2])
    with col_ref:
        if st.button("🔄 Actualizar lista"):
            st.rerun()
    with col_link:
        st.markdown("[📊 **Abrir hoja de Google Sheets completa**](https://docs.google.com/spreadsheets/d/1j6sczaZUeuds1bF1mzzHYHgSuy52q1nBbNeaCukg19M/edit?usp=sharing)")

    if not df_turnos.empty and "padre" in df_turnos.columns:
        # Filtrar solo registros del mes actual (YYYY-MM)
        mes_prefijo = hoy.strftime("%Y-%m")
        if "fecha" in df_turnos.columns:
            df_turnos["fecha_corta"] = df_turnos["fecha"].astype(str).str.strip().str[:10]
            df_mes = df_turnos[df_turnos["fecha_corta"].str.startswith(mes_prefijo)].copy()
        else:
            df_mes = pd.DataFrame()

        df_mostrar = df_mes if not df_mes.empty else df_turnos

        cols_deseadas = [c for c in ["dia", "fecha", "turno", "padre", "estudiante", "grado"] if c in df_mostrar.columns]
        vista = df_mostrar[cols_deseadas].sort_values(by="fecha", ascending=True).copy()
        vista.columns = [c.capitalize() for c in cols_deseadas]
        
        st.dataframe(vista, use_container_width=True, hide_index=True)
    else:
        st.info(f"Todavía no hay turnos registrados para el mes de {mes_actual_nombre}.")
