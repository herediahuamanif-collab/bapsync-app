import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
import requests

# 1. Configuración de página
st.set_page_config(page_title="BapSync - Turnos BAPES", page_icon="🛡️", layout="centered")

# Estilos visuales acordes al logo
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

# URL DE LA API DE GOOGLE SHEETS (Se lee desde Secrets o variable)
API_URL = st.secrets.get("SHEET_API_URL", "")

def cargar_turnos():
    if not API_URL:
        return pd.DataFrame(columns=['fecha', 'dia', 'turno', 'padre', 'telefono', 'estudiante', 'grado', 'creado'])
    try:
        res = requests.get(API_URL, timeout=10, allow_redirects=True)
        if res.status_code == 200:
            datos = res.json()
            return pd.DataFrame(datos) if datos else pd.DataFrame(columns=['fecha', 'dia', 'turno', 'padre', 'telefono', 'estudiante', 'grado', 'creado'])
        return pd.DataFrame(columns=['fecha', 'dia', 'turno', 'padre', 'telefono', 'estudiante', 'grado', 'creado'])
    except Exception:
        return pd.DataFrame(columns=['fecha', 'dia', 'turno', 'padre', 'telefono', 'estudiante', 'grado', 'creado'])

# 2. Logo centrado
col_izq, col_centro, col_der = st.columns([1, 4, 1])
with col_centro:
    try:
        st.image("logo_bapsync.png", use_container_width=True)
    except Exception:
        st.markdown("<h2 style='text-align: center; color: #0c5c3c;'>🛡️ BapSync</h2>", unsafe_allow_html=True)

st.markdown("<div class='banner-card'><b>Seguridad Escolar BAPES</b><br>Turnos: Mañana (7:30 - 8:15) y Tarde (2:15 - 3:00) | Máx. 5 padres por turno</div>", unsafe_allow_html=True)

# 3. Cálculo de la semana actual (Lunes a Viernes)
hoy = datetime.today()
lunes = hoy - timedelta(days=hoy.weekday())
nombres_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
dias_dict = {}

for i in range(5):
    f = lunes + timedelta(days=i)
    etiqueta = f"{nombres_dias[i]} {f.strftime('%d/%m')}"
    dias_dict[etiqueta] = {
        "fecha_str": f.strftime("%Y-%m-%d"),
        "dia": nombres_dias[i]
    }

df_turnos = cargar_turnos()

# 4. Pestañas
tab_registro, tab_horario = st.tabs(["📝 Inscribirme a un Turno", "📅 Ver Horario Semanal"])

with tab_registro:
    st.markdown("#### Selecciona la fecha y hora para asistir a BAPES:")
    
    dia_elegido_label = st.selectbox("📅 Día de asistencia (Esta semana):", list(dias_dict.keys()))
    info_dia = dias_dict[dia_elegido_label]
    
    turnos_disponibles = [
        "🌅 Mañana: 07:30 a 08:15 (Entrada)",
        "🌇 Tarde: 02:15 a 03:00 (Salida)"
    ]
    turno_elegido = st.radio("⏰ Turno:", turnos_disponibles)

    # Validar cupos en tiempo real
    if not df_turnos.empty and "fecha" in df_turnos.columns and "turno" in df_turnos.columns:
        ocupados = len(df_turnos[
            (df_turnos["fecha"].astype(str) == info_dia["fecha_str"]) & 
            (df_turnos["turno"].astype(str) == turno_elegido)
        ])
    else:
        ocupados = 0

    libres = 5 - ocupados

    if libres > 0:
        st.info(f"✅ Cupos disponibles: **{libres} de 5**")
    else:
        st.error("❌ Turno completo (5/5 padres ya registrados). Elige otro horario.")

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
            st.error("Falta configurar la URL de la base de datos en los Secrets de Streamlit.")
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
                # allow_redirects=True sigue la redirección 302 estándar de Google Apps Script
                r = requests.post(API_URL, json=payload, timeout=15, allow_redirects=True)
                
                # Google Apps Script responde 200 tras seguir la redirección o texto con status ok
                if r.status_code in [200, 302] or "ok" in r.text:
                    st.success("🎉 ¡Tu turno ha sido registrado correctamente!")
                    mensaje_wa = f"Hola {nombre_padre}, confirmaste tu turno en BAPES para el {dia_elegido_label} en el horario {turno_elegido}. ¡Gracias por cuidar la seguridad escolar!"
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
                    st.error(f"Error al guardar: Código {r.status_code} - Respuesta: {r.text[:120]}")
            except Exception as ex:
                st.error(f"Error de conexión: {ex}")

with tab_horario:
    st.markdown("#### 📋 Horario de Vigilancia BAPES (Semana Actual)")
    
    fechas_semana = [d["fecha_str"] for d in dias_dict.values()]
    if not df_turnos.empty and "fecha" in df_turnos.columns:
        df_esta_semana = df_turnos[df_turnos["fecha"].astype(str).isin(fechas_semana)]
    else:
        df_esta_semana = pd.DataFrame()

    if not df_esta_semana.empty:
        vista_publica = df_esta_semana[["dia", "fecha", "turno", "padre", "estudiante", "grado"]].copy()
        vista_publica.columns = ["Día", "Fecha", "Turno", "Apoderado", "Estudiante", "Grado"]
        st.dataframe(vista_publica, use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay turnos ocupados esta semana. ¡Sé el primero en registrarte!")
