import streamlit as st
from groq import Groq
import os
from pypdf import PdfReader
from docx import Document
import pandas as pd
from pptx import Presentation
import io

# Configuración visual
st.set_page_config(page_title="EVANS.DA 🚀", page_icon="🤖", layout="centered")

# CSS para pegar el botón de subida al input
st.markdown("""
    <style>
    .stChatInputContainer {
        padding-bottom: 1rem;
    }
    /* Estilo para que el uploader parezca un botón pequeño */
    section[data-testid="stFileUploadDropzone"] {
        padding: 0px !important;
        border: none !important;
        background-color: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 EVANS.DA")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def procesar_archivo(file_name, file_content):
    texto = f"\n--- Fuente: {file_name} ---\n"
    try:
        if file_name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_content))
            for page in reader.pages: texto += (page.extract_text() or "") + "\n"
        elif file_name.endswith(".docx"):
            doc = Document(io.BytesIO(file_content))
            for para in doc.paragraphs: texto += para.text + "\n"
        elif file_name.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(file_content))
            texto += df.to_string() + "\n"
        return texto
    except Exception as e:
        return f"\nError en {file_name}: {e}\n"

# --- ZONA DE CHAT E INPUT ESTILO CHATGPT ---

# 1. Contenedor para el historial de mensajes
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. Barra inferior flotante con Columnas
# Usamos columnas para poner el botón "+" y el input en la misma línea visual
col1, col2 = st.columns([0.1, 0.9])

with col1:
    # El cargador de archivos ahora es solo un icono de "+"
    uploaded_files = st.file_uploader("➕", accept_multiple_files=True, label_visibility="collapsed")

with col2:
    prompt = st.chat_input("Pregunta lo que quieras...")

# 3. Lógica de Respuesta
if prompt:
    # Guardamos y mostramos mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Procesamos archivos (los de la carpeta 'data' + los recién subidos)
    contexto_total = ""
    # Archivos en carpeta fija
    if os.path.exists("data"):
        for root, dirs, files in os.walk("data"):
            for archivo in files:
                with open(os.path.join(root, archivo), "rb") as f:
                    contexto_total += procesar_archivo(archivo, f.read())
    
    # Archivos subidos dinámicamente
    if uploaded_files:
        for uploaded_file in uploaded_files:
            contexto_total += procesar_archivo(uploaded_file.name, uploaded_file.read())

    # Generamos respuesta de la IA
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                instrucciones = f"Eres EVANS.DA. Contexto: {contexto_total[:15000]}"
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "system", "content": instrucciones}, {"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                )
                respuesta = chat_completion.choices[0].message.content
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
            except Exception as e:
                st.error(f"Error: {e}")