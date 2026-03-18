import streamlit as st
from groq import Groq
import os
from pypdf import PdfReader
from docx import Document
import pandas as pd
from pptx import Presentation
import io

# Configuración visual estilo ChatGPT
st.set_page_config(page_title="EVANS.DA 🚀", page_icon="🤖", layout="centered")

# CSS para mejorar la estética del área de archivos
st.markdown("""
    <style>
    .stChatInputContainer {padding-bottom: 20px;}
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
        elif file_name.endswith(".pptx"):
            prs = Presentation(io.BytesIO(file_content))
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"): texto += shape.text + "\n"
        return texto
    except Exception as e:
        return f"\nError en {file_name}: {e}\n"

# --- ZONA DE SUBIDA (Estilo Gemini) ---
# Colocamos el cargador justo antes del chat_input
with st.container():
    uploaded_files = st.file_uploader("📎 Añade archivos (PDF, Word, Excel, PPT)", 
                                    accept_multiple_files=True, 
                                    label_visibility="collapsed")

# Cargar conocimiento de carpeta 'data' y archivos subidos
contexto_total = ""
if os.path.exists("data"):
    for root, dirs, files in os.walk("data"):
        for archivo in files:
            with open(os.path.join(root, archivo), "rb") as f:
                contexto_total += procesar_archivo(archivo, f.read())

if uploaded_files:
    for uploaded_file in uploaded_files:
        contexto_total += procesar_archivo(uploaded_file.name, uploaded_file.read())

# Historial de Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de usuario (Barra inferior)
if prompt := st.chat_input("Escribe tu mensaje aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
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