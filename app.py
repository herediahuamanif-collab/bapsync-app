import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
from streamlit_gsheets import GSheetsConnection

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

# 2. Conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_turnos():
    try:
        df = conn.read(ttl=3)
        return df if not df.empty else pd.DataFrame(columns=['fecha', 'dia', 'turno', 'padre', 'telefono', 'estudiante', 'grado', 'creado'])
    except Exception:
        return pd.DataFrame(columns=['fecha', 'dia', 'turno', 'padre', 'telefono', 'estudiante', 'grado', 'creado'])

# 3. Logo centrado
col_izq, col_centro, col_der = st.columns([1, 4, 1])
with col_centro:
    try:
        st.image("logo_bapsync.png", use_container_width=True)
    except:
        st.markdown("<h2 style='text-align: center; color: #0c5c3c;'>🛡️ BapSync</h2>", unsafe_allow_html=True)

st.markdown("<div class='banner-card'><b>Seguridad Escolar BAPES</b><br>Turnos: Mañana (7:30 - 8:15) y Tarde (2:15 - 3:00) | Máx. 5 padres por turno</div>", unsafe_allow_html=True)

# 4. Cálculo automático de la semana actual (Lunes a Viernes)
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

# 5. Pestañas principales
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

    # Validar cupos (Máx 5)
    if not df_turnos.empty:
        ocupados = len(df_turnos[
            (df_turnos["fecha"] == info_dia["fecha_str"]) & 
            (df_turnos["turno"] == turno_elegido)
        ])
    else:
        ocupados = 0

    libres = 5 - ocupados

    if libres > 0:
        st.info(f"✅ Cupos disponibles: **{libres} de 5**")
    else:
        st.error("❌ Turno completo (5/5 padres ya registrados). Elige otro turno o día.")

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
        else:
            nuevo = pd.DataFrame([{
                "fecha": info_dia["fecha_str"],
                "dia": info_dia["dia"],
                "turno": turno_elegido,
                "padre": nombre_padre.strip(),
                "telefono": telefono_padre.strip(),
                "estudiante": estudiante.strip(),
                "grado": grado.strip(),
                "creado": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
            
            df_actualizado = pd.concat([df_turnos, nuevo], ignore_index=True)
            conn.update(data=df_actualizado)
            st.cache_data.clear()
            
            st.success("🎉 ¡Tu turno ha sido registrado correctamente!")
            
            mensaje_wa = f"Hola {nombre_padre}, confirmaste tu turno en BAPES para el {dia_elegido_label} en el horario {turno_elegido}. ¡Gracias por cuidar la seguridad escolar de los estudiantes!"
            url_whatsapp = f"https://wa.me/51{telefono_padre}?text={urllib.parse.quote(mensaje_wa)}"
            
            st.markdown(f"""
                <div style='text-align: center; margin-top: 10px;'>
                    <a href='{url_whatsapp}' target='_blank' style='background-color:#25D366; color:white; padding:10px 18px; border-radius:8px; text-decoration:none; font-weight:bold; display:inline-block;'>
                        📲 Enviar recordatorio a mi WhatsApp
                    </a>
                </div>
            """, unsafe_allow_html=True)

with tab_horario:
    st.markdown("#### 📋 Horario de Vigilancia BAPES (Semana Actual)")
    
    fechas_semana = [d["fecha_str"] for d in dias_dict.values()]
    df_esta_semana = df_turnos[df_turnos["fecha"].isin(fechas_semana)] if not df_turnos.empty else pd.DataFrame()

    if not df_esta_semana.empty:
        vista_publica = df_esta_semana[["dia", "fecha", "turno", "padre", "estudiante", "grado"]].copy()
        vista_publica.columns = ["Día", "Fecha", "Turno", "Apoderado", "Estudiante", "Grado"]
        st.dataframe(vista_publica, use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay turnos ocupados esta semana. ¡Sé el primero en registrarte!")
