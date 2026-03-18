import streamlit as st
from groq import Groq
import os
from pypdf import PdfReader
from docx import Document
import pandas as pd
from pptx import Presentation
import io

# 1. Configuración de página
st.set_page_config(page_title="EVANS.DA 🚀", page_icon="🤖", layout="centered")

# --- CSS PARA EL EFECTO CHATGPT ---
st.markdown("""
    <style>
    /* Deja espacio al final para que los mensajes no queden tapados por la barra fija */
    .main .block-container {
        padding-bottom: 200px;
    }

    /* Estiliza el cargador de archivos para que sea una barra delgada sobre el chat */
    .stFileUploadDropzone {
        min-height: 0px !important;
        padding: 5px !important;
        border-radius: 12px !important;
        background-color: #f0f2f6 !important;
        border: 1px solid #ddd !important;
    }
    .stFileUploadDropzone div div {
        display: none; /* Oculta textos largos innecesarios */
    }
    .stFileUploadDropzone::before {
        content: '📎 Adjuntar archivos pesados (PDF, Word, Excel, PPT)';
        font-size: 13px;
        color: #555;
        text-align: center;
        display: block;
        padding: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 EVANS.DA")

# Cliente de Groq
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Función para procesar documentos
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

# 2. Historial de Chat (Se renderiza en el flujo normal de la página)
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 3. ÁREA DE ENTRADA (MÁGICAMENTE FIJA ABAJO) ---
# Al colocar el uploader justo antes del chat_input, Streamlit los mantiene juntos al fondo
archivos_nuevos = st.file_uploader("", accept_multiple_files=True, label_visibility="collapsed")
prompt = st.chat_input("Escribe tu mensaje aquí...")

if prompt:
    # Mostrar mensaje del usuario inmediatamente
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Recopilar todo el contexto (Data fija + Subidos ahora)
    contexto_total = ""
    if os.path.exists("data"):
        for root, dirs, files in os.walk("data"):
            for archivo in files:
                with open(os.path.join(root, archivo), "rb") as f:
                    contexto_total += procesar_archivo(archivo, f.read())
    
    if archivos_nuevos:
        for f in archivos_nuevos:
            contexto_total += procesar_archivo(f.name, f.read())

    # Generar respuesta de la IA
    with st.chat_message("assistant"):
        with st.spinner("EVANS.DA está pensando..."):
            try:
                instrucciones = f"Eres EVANS.DA. Responde usando este contexto: {contexto_total[:15000]}"
                completion = client.chat.completions.create(
                    messages=[{"role": "system", "content": instrucciones}, {"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                )
                respuesta = completion.choices[0].message.content
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
                
                # Forzar scroll al final para ver la respuesta completa
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")