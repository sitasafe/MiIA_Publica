import streamlit as st
from groq import Groq
import os
from pypdf import PdfReader
from docx import Document
import pandas as pd
from pptx import Presentation
import io

# 1. Configuración de página y estilo CSS
st.set_page_config(page_title="EVANS.DA 🚀", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    /* Hace que el cargador de archivos sea una barra delgada y estética */
    .stFileUploadDropzone {
        min-height: 0px !important;
        padding: 8px !important;
        border-radius: 12px !important;
        background-color: #f8f9fb !important;
        border: 1px solid #e0e0e0 !important;
    }
    /* Oculta los textos largos del cargador de archivos para que sea minimalista */
    .stFileUploadDropzone div div {
        display: none;
    }
    /* Añade un pequeño texto descriptivo antes del cargador */
    .stFileUploadDropzone::before {
        content: '📎 Haz clic o arrastra archivos aquí (PDF, Word, Excel, PPT)';
        font-size: 14px;
        color: #666;
        display: block;
        text-align: center;
        margin-bottom: 5px;
    }
    /* Ajusta el espacio del chat para que no choque con la barra fija */
    .main .block-container {
        padding-bottom: 160px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 EVANS.DA")

# Cliente de Groq
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Función para procesar archivos
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

# 2. Historial de Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 3. ÁREA DE ENTRADA (ARCHIVOS ARRIBA, TEXTO ABAJO) ---
# Al no usar columnas, el diseño se mantiene estable en cualquier pantalla
with st.container():
    archivos_nuevos = st.file_uploader("", accept_multiple_files=True, label_visibility="collapsed")
    prompt = st.chat_input("Pregunta lo que quieras...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Construcción del contexto (Carpeta data + Archivos subidos)
    contexto_total = ""
    if os.path.exists("data"):
        for root, dirs, files in os.walk("data"):
            for archivo in files:
                with open(os.path.join(root, archivo), "rb") as f:
                    contexto_total += procesar_archivo(archivo, f.read())
    
    if archivos_nuevos:
        for f in archivos_nuevos:
            contexto_total += procesar_archivo(f.name, f.read())

    # Respuesta de la IA
    with st.chat_message("assistant"):
        with st.spinner("Analizando información..."):
            try:
                # Tomamos los últimos 15,000 caracteres para el contexto
                instrucciones = f"Eres EVANS.DA. Usa este contexto para responder: {contexto_total[:15000]}"
                completion = client.chat.completions.create(
                    messages=[{"role": "system", "content": instrucciones}, {"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                )
                respuesta = completion.choices[0].message.content
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
            except Exception as e:
                st.error(f"Error en la IA: {e}")