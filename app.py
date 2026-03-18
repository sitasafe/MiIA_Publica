import streamlit as st
from groq import Groq
import os
from pypdf import PdfReader
from docx import Document
import pandas as pd
from pptx import Presentation
import io
from streamlit_google_auth import Authenticate

# 1. Configuración de página
st.set_page_config(page_title="EVANS.DA 🚀", page_icon="🤖", layout="wide")

# --- CSS PARA ESTILO CHATGPT / PERPLEXITY ---
st.markdown("""
    <style>
    .main .block-container { padding-bottom: 150px; }
    div[data-testid="stHorizontalBlock"] {
        align-items: center;
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #eee;
    }
    .stChatInputContainer { padding-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- MANEJO ROBUSTO DE SECRETOS ---
# Esta lógica previene el TypeError buscando en ambos lugares posibles
try:
    if "google_auth" in st.secrets:
        auth_data = st.secrets["google_auth"]
    else:
        auth_data = st.secrets
    
    # Extraer valores con seguridad
    s_key = auth_data["secret_key"]
    c_id = auth_data["client_id"]
    c_sec = auth_data["client_secret"]
    r_uri = auth_data["redirect_uri"]
except Exception as e:
    st.error(f"Error cargando secretos: {e}")
    st.stop()

# --- LOGIN REAL CON GOOGLE ---
authenticator = Authenticate(
    secret_key=s_key,
    cookie_name='evans_da_auth',
    cookie_key='evans_da_cookie',
    client_id=c_id,
    client_secret=c_sec,
    redirect_uri=r_uri,
)

authenticator.check_authenticity()

if not st.session_state.get('connected'):
    st.title("🤖 Bienvenido a EVANS.DA")
    st.info("Inicia sesión con tu cuenta de Google para acceder a tus herramientas de maestría.")
    authenticator.login()
    st.stop()

# --- SI ESTÁ CONECTADO, INICIA LA APP ---
user_info = st.session_state.get('user_info')

# Inicializar estados de chat y gemas
if "chats" not in st.session_state: st.session_state.chats = {"Nueva Consulta": []}
if "current_chat" not in st.session_state: st.session_state.current_chat = "Nueva Consulta"
if "gemas" not in st.session_state: 
    st.session_state.gemas = {"Estándar": "Eres EVANS.DA, un asistente útil."}

# --- SIDEBAR (HISTORIAL Y GEMAS) ---
with st.sidebar:
    if user_info:
        st.write(f"👤 {user_info.get('email')}")
    st.title("💎 Mis Gemas")
    gema_actual = st.selectbox("IA activa:", list(st.session_state.gemas.keys()))
    
    with st.expander("➕ Crear Gema (Proyecto)"):
        n_gema = st.text_input("Nombre:")
        i_gema = st.text_area("Instrucciones:")
        if st.button("Guardar"):
            st.session_state.gemas[n_gema] = i_gema
            st.rerun()
            
    st.divider()
    if st.button("🗑️ Borrar Historial"):
        st.session_state.chats = {"Nueva Consulta": []}
        st.rerun()
    if st.button("🚪 Salir"):
        authenticator.logout()
        st.rerun()

# --- LÓGICA DE PROCESAMIENTO ---
def leer_archivo(f):
    content = ""
    if f.name.endswith(".pdf"):
        pdf = PdfReader(f)
        for page in pdf.pages: content += (page.extract_text() or "")
    elif f.name.endswith(".docx"):
        doc = Document(f)
        for p in doc.paragraphs: content += p.text + "\n"
    return content

# --- INTERFAZ DE CHAT ---
st.title(f"🤖 EVANS.DA: {gema_actual}")

# Mostrar mensajes previos
for msg in st.session_state.chats[st.session_state.current_chat]:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# --- BARRA DE ENTRADA TIPO PERPLEXITY ---
with st.container():
    col1, col2 = st.columns([0.1, 0.9])
    with col1:
        opciones = st.popover("➕")
        with opciones:
            st.write("📂 Adjuntar archivos")
            files = st.file_uploader("Sube PDF o Word", accept_multiple_files=True, label_visibility="collapsed")
            pensar = st.toggle("Modo Analítico (Pensar)")
    
    with col2:
        prompt = st.chat_input("Escribe tu consulta o pide ayuda con tu investigación...")

if prompt:
    st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    contexto = ""
    if files:
        for f in files: contexto += leer_archivo(f)

    # Respuesta de la IA
    with st.chat_message("assistant"):
        with st.spinner("Generando respuesta..."):
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            system_prompt = st.session_state.gemas[gema_actual]
            if pensar: system_prompt += " Analiza profundamente y responde paso a paso."
            
            res = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": f"{system_prompt}\nContexto: {contexto[:12000]}"},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
            ).choices[0].message.content
            
            st.markdown(res)
            st.session_state.chats[st.session_state.current_chat].append({"role": "assistant", "content": res})
            st.rerun()