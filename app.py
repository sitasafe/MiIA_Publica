import streamlit as st
from groq import Groq
import os
from pypdf import PdfReader
from docx import Document
import pandas as pd
from pptx import Presentation
import io

# Configuración visual
st.set_page_config(page_title="EVANS.DA Inteligencia Total 🚀", page_icon="🤖", layout="wide")
st.title("🤖 EVANS.DA: Asistente Inteligente")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- FUNCIÓN PARA PROCESAR CUALQUIER ARCHIVO ---
def procesar_archivo(file_name, file_content):
    texto = f"\n--- Contenido de: {file_name} ---\n"
    try:
        if file_name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_content))
            for page in reader.pages:
                texto += page.extract_text() + "\n"
        elif file_name.endswith(".docx"):
            doc = Document(io.BytesIO(file_content))
            for para in doc.paragraphs:
                texto += para.text + "\n"
        elif file_name.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(file_content))
            texto += df.to_string() + "\n"
        elif file_name.endswith(".pptx"):
            prs = Presentation(io.BytesIO(file_content))
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        texto += shape.text + "\n"
        return texto
    except Exception as e:
        return f"\nError leyendo {file_name}: {e}\n"

# --- 1. BARRA LATERAL PARA SUBIR ARCHIVOS ---
with st.sidebar:
    st.header("📁 Centro de Datos")
    uploaded_files = st.file_uploader("Sube PDF, Word, Excel o PPT", accept_multiple_files=True)
    st.info("Los archivos subidos aquí se sumarán a los que ya tienes en la carpeta 'data'.")

# --- 2. CARGAR CONOCIMIENTO (CARPETA DATA + SUBIDOS) ---
contexto_total = ""

# Leer archivos fijos de la carpeta 'data'
if os.path.exists("data"):
    for root, dirs, files in os.walk("data"):
        for archivo in files:
            with open(os.path.join(root, archivo), "rb") as f:
                contexto_total += procesar_archivo(archivo, f.read())

# Leer archivos subidos por el usuario en el momento
if uploaded_files:
    for uploaded_file in uploaded_files:
        contexto_total += procesar_archivo(uploaded_file.name, uploaded_file.read())

# --- 3. INTERFAZ DE CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Pregúntame lo que necesites..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando documentos y generando respuesta..."):
            try:
                instrucciones = f"""
                Eres EVANS.DA, una IA avanzada de conocimiento general y experto en los documentos proporcionados.
                
                CONTEXTO DISPONIBLE:
                {contexto_total[:12000]} 
                
                INSTRUCCIONES:
                1. Usa el contexto para responder dudas específicas.
                2. Si la duda es general, usa tu conocimiento global.
                3. Responde siempre de forma profesional y amable en español.
                """
                
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "system", "content": instrucciones}, {"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                )
                respuesta = chat_completion.choices[0].message.content
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
            except Exception as e:
                st.error(f"Error: {e}")