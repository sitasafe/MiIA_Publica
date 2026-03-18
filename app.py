import streamlit as st
from groq import Groq
import os
from pypdf import PdfReader
from docx import Document
import io
from streamlit_google_auth import Authenticate

# 1. Configuración de página
st.set_page_config(page_title="EVANS.DA 🚀", page_icon="🤖", layout="centered")

# --- CSS AVANZADO PARA EL MENÚ FLOTANTE ---
st.markdown("""
    <style>
    .main .block-container { padding-bottom: 150px; }
    
    /* Estilo para que el input y el botón parezcan una sola barra */
    div[data-testid="stHorizontalBlock"] {
        align-items: end;
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 20px;
        border: 1px solid #ddd;
    }
    
    /* Ocultar bordes del popover para que parezca un botón de "+" */
    button[data-testid="stBaseButton-secondary"] {
        border-radius: 50% !important;
        width: 40px !important;
        height: 40px !important;
        padding: 0px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE AUTENTICACIÓN ---
authenticator = Authenticate(
    secret_key=st.secrets["google_auth"]["secret_key"],
    cookie_name='evans_da_auth',
    cookie_key='evans_da_cookie',
    client_id=st.secrets["google_auth"]["client_id"],
    client_secret=st.secrets["google_auth"]["client_secret"],
    redirect_uri=st.secrets["google_auth"]["redirect_uri"],
)

authenticator.check_authenticity()

if not st.session_state.get('connected'):
    st.title("🤖 Bienvenido a EVANS.DA")
    authenticator.login()
    st.stop()

# --- DATOS DEL USUARIO Y ESTADOS ---
user_info = st.session_state.get('user_info')
if "chats" not in st.session_state: st.session_state.chats = {"Nueva Consulta": []}
if "current_chat" not in st.session_state: st.session_state.current_chat = "Nueva Consulta"
if "gemas" not in st.session_state: st.session_state.gemas = {"Estándar": "Eres EVANS.DA, un asistente profesional."}
if "selected_gema" not in st.session_state: st.session_state.selected_gema = "Estándar"

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"👤 {user_info.get('email')}")
    st.title("💎 Gemas")
    st.session_state.selected_gema = st.selectbox("IA activa:", list(st.session_state.gemas.keys()))
    
    with st.expander("✨ Crear Gema"):
        n = st.text_input("Nombre:")
        i = st.text_area("Instrucciones:")
        if st.button("Guardar"):
            st.session_state.gemas[n] = i
            st.rerun()
    st.divider()
    if st.button("➕ Nuevo Chat", use_container_width=True):
        id_c = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[id_c] = []
        st.session_state.current_chat = id_c
        st.rerun()

# --- INTERFAZ DE CHAT ---
st.title("🤖 EVANS.DA")

# Mostrar mensajes
for msg in st.session_state.chats[st.session_state.current_chat]:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# --- BARRA DE ENTRADA TIPO PERPLEXITY ---
# Creamos un contenedor fijo al fondo mediante columnas
with st.container():
    col1, col2 = st.columns([0.1, 0.9])
    
    with col1:
        # El botón "+" usando un Popover (Menú desplegable)
        menu = st.popover("➕")
        with menu:
            st.markdown("### Herramientas")
            archivos = st.file_uploader("Añadir archivos", accept_multiple_files=True, label_visibility="collapsed")
            pensar = st.checkbox("💡 Modo Pensar")
            web_search = st.checkbox("🌐 Búsqueda Internet")
    
    with col2:
        prompt = st.chat_input("Pregunta lo que quieras...")

if prompt:
    # 1. Guardar mensaje usuario
    st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": prompt})
    
    # 2. Procesar archivos si los hay
    contexto = ""
    if archivos:
        for f in archivos:
            if f.name.endswith(".pdf"):
                reader = PdfReader(f)
                for page in reader.pages: contexto += page.extract_text()
            elif f.name.endswith(".docx"):
                doc = Document(f)
                for p in doc.paragraphs: contexto += p.text + "\n"

    # 3. Respuesta IA
    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            inst = st.session_state.gemas[st.session_state.selected_gema]
            
            # Ajustar instrucciones si "Modo Pensar" está activo
            if pensar: inst += " Responde de forma muy analítica y detallada paso a paso."
            
            res = client.chat.completions.create(
                messages=[{"role": "system", "content": f"{inst}\nContexto: {contexto[:10000]}"}, {"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            ).choices[0].message.content
            
            st.markdown(res)
            st.session_state.chats[st.session_state.current_chat].append({"role": "assistant", "content": res})
            st.rerun()