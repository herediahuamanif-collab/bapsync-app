import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
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
    .card-recordatorio {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #25D366;
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 10px;
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

def generar_enlace_google_calendar(fecha_str, turno, padre, estudiante):
    # Definir horas según el turno elegido (Zona horaria Lima UTC-5)
    # Formato UTC: YYYYMMDDTHHMMSSZ (UTC-5 significa sumar 5 horas para UTC)
    f = fecha_str.replace("-", "")
    if "Mañana" in turno:
        # 07:30 a 08:15 local -> 12:30 a 13:15 UTC
        start_time = f"{f}T123000Z"
        end_time = f"{f}T131500Z"
    else:
        # 14:15 a 15:00 local -> 19:15 a 20:00 UTC
        start_time = f"{f}T191500Z"
        end_time = f"{f}T200000Z"

    titulo = f"🛡️ Turno BAPES: Seguridad Escolar"
    detalles = (
        f"Apoderado: {padre}\n"
        f"Estudiante: {estudiante}\n"
        f"Turno: {turno}\n\n"
        f"Recuerda asistir puntualmente con tu chaleco/distintivo BAPES para resguardar la entrada o salida de los estudiantes."
    )
    ubicacion = "Puerta Principal del Colegio"

    params = {
        "action": "TEMPLATE",
        "text": titulo,
        "dates": f"{start_time}/{end_time}",
        "details": detalles,
        "location": ubicacion
    }
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

# 2. Logo institucional
col_izq, col_centro, col_der = st.columns([1, 4, 1])
with col_centro:
    try:
        st.image("logo_bapsync.png", use_container_width=True)
    except Exception:
        st.markdown("<h2 style='text-align: center; color: #0c5c3c;'>🛡️ BapSync</h2>", unsafe_allow_html=True)

# 3. Lógica mensual dinámica
hoy = datetime.today()
meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

mes_actual_nombre = meses_nombres[hoy.month - 1]
total_dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
fecha_hoy_str = hoy.strftime("%Y-%m-%d")

st.markdown(f"<div class='banner-card'><b>Seguridad Escolar BAPES — Mes de {mes_actual_nombre} {hoy.year}</b><br>Turnos: Mañana (7:30 - 8:15) y Tarde (2:15 - 3:00) | Máx. 5 padres por turno</div>", unsafe_allow_html=True)

# Generar días hábiles del mes
dias_mes_dict = {}
for dia_num in range(1, total_dias_mes + 1):
    fecha_obj = datetime(hoy.year, hoy.month, dia_num)
    if fecha_obj.weekday() < 5:
        nombre_d = dias_nombres[fecha_obj.weekday()]
        etiqueta = f"{nombre_d} {dia_num:02d} de {mes_actual_nombre}"
        dias_mes_dict[etiqueta] = {
            "fecha_str": fecha_obj.strftime("%Y-%m-%d"),
            "dia": nombre_d,
            "dia_num": dia_num
        }

df_turnos = cargar_turnos()

# 4. Pestañas principales
tab_registro, tab_horario, tab_notif = st.tabs(["📝 Inscribirme a un Turno", "📅 Ver Rol Mensual", "🔔 Avisar a Padres de Hoy"])

with tab_registro:
    st.markdown(f"#### Selecciona tu fecha en {mes_actual_nombre} y turno:")
    
    dia_elegido_label = st.selectbox("📅 Día de asistencia (Lunes a Viernes):", list(dias_mes_dict.keys()))
    info_dia = dias_mes_dict[dia_elegido_label]
    
    turnos_disponibles = [
        "🌅 Mañana: 07:30 a 08:15 (Entrada)",
        "🌇 Tarde: 02:15 a 03:00 (Salida)"
    ]
    turno_elegido = st.radio("⏰ Turno:", turnos_disponibles)

    # Validar cupos en tiempo real
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
        st.error(f"❌ Turno completo (5/5 padres ya registrados). Elige otro día u horario.")

    st.markdown("##### Tus Datos:")
    nombre_padre = st.text_input("Nombre y Apellidos del Apoderado:")
    telefono_padre = st.text_input("Número de Celular / WhatsApp (9 dígitos):", max_chars=9)
    estudiante = st.text_input("Nombre del Estudiante:")
    grado = st.text_input("Grado y Sección:")

    if st.button("Confirmar mi Turno en BAPES"):
        if not (nombre_padre and telefono_padre and estudiante):
            st.warning("⚠️ Por favor completa tu nombre, celular y nombre del estudiante.")
        elif libres <= 0:
            st.error("Lo sentimos, este turno ya está completo.")
        elif not API_URL:
            st.error("Falta configurar la URL de la base de datos en Secrets.")
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
                    
                    # Generación de enlaces de recordatorio
                    url_calendar = generar_enlace_google_calendar(
                        info_dia["fecha_str"], turno_elegido, nombre_padre, estudiante
                    )
                    
                    mensaje_wa = f"Hola {nombre_padre}, confirmaste tu turno en BAPES para el {dia_elegido_label} en el horario {turno_elegido}. ¡Gracias por apoyar en la seguridad escolar!"
                    url_whatsapp = f"https://wa.me/51{telefono_padre}?text={urllib.parse.quote(mensaje_wa)}"
                    
                    st.markdown("### 🔔 Activa tu recordatorio automático:")
                    
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        st.markdown(f"""
                            <a href='{url_calendar}' target='_blank' style='display:block; text-align:center; background-color:#1a73e8; color:white; padding:12px 10px; border-radius:8px; text-decoration:none; font-weight:bold;'>
                                📅 Guardar en Google Calendar
                            </a>
                        """, unsafe_allow_html=True)
                    with col_b2:
                        st.markdown(f"""
                            <a href='{url_whatsapp}' target='_blank' style='display:block; text-align:center; background-color:#25D366; color:white; padding:12px 10px; border-radius:8px; text-decoration:none; font-weight:bold;'>
                                📲 Recibir en WhatsApp
                            </a>
                        """, unsafe_allow_html=True)
                    
                    st.caption("💡 Si presionas **Guardar en Google Calendar**, tu teléfono te notificará automáticamente 24 horas y 1 hora antes de tu turno.")
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

with tab_notif:
    st.markdown(f"#### 🔔 Enviar Recordatorio a los Padres de Hoy ({hoy.strftime('%d/%m/%Y')})")
    st.caption("Esta sección permite a la coordinadora avisar a los apoderados que les toca asistir hoy con un solo clic.")

    if not df_turnos.empty and "fecha" in df_turnos.columns:
        df_turnos["fecha_corta"] = df_turnos["fecha"].astype(str).str.strip().str[:10]
        padres_hoy = df_turnos[df_turnos["fecha_corta"] == fecha_hoy_str]

        if not padres_hoy.empty:
            st.success(f"Hay **{len(padres_hoy)} padre(s)** asignados para el día de hoy.")
            
            for _, fila in padres_hoy.iterrows():
                padre_nom = fila.get("padre", "Apoderado")
                turno_nom = fila.get("turno", "Turno BAPES")
                tel = str(fila.get("telefono", "")).replace(".0", "").strip()
                est = fila.get("estudiante", "el estudiante")

                msg_hoy = (
                    f"Estimado/a {padre_nom}, le recordamos que el día de hoy le toca asistir a su turno de seguridad BAPES en el horario: {turno_nom}, "
                    f"apoyando en la seguridad de su hijo/a {est}. ¡Agradecemos su puntualidad!"
                )
                url_aviso = f"https://wa.me/51{tel}?text={urllib.parse.quote(msg_hoy)}"

                st.markdown(f"""
                    <div class='card-recordatorio'>
                        <b>👤 {padre_nom}</b> — <i>{turno_nom}</i><br>
                        Estudiante: {est} | Celular: {tel}<br><br>
                        <a href='{url_aviso}' target='_blank' style='background-color:#25D366; color:white; padding:6px 14px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:14px; display:inline-block;'>
                            📲 Enviar Recordatorio por WhatsApp
                        </a>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Para el día de hoy no hay turnos agendados.")
    else:
        st.info("No hay registros en el sistema todavía.")
