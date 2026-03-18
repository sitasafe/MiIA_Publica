import streamlit as st
from groq import Groq
import os
from pypdf import PdfReader
from docx import Document
import pandas as pd
from pptx import Presentation

# Configuración inicial
st.set_page_config(page_title="EVANS.DA Multiformato 🚀", page_icon="📊")
st.title("🚀 EVANS.DA: Inteligencia Total")
st.caption("Lectura de PDF, Word, Excel, PPT + Conocimiento Global")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- FUNCIÓN PARA LEER TODOS LOS FORMATOS EN DATA ---
def extraer_contenido_multiformato():
    texto_acumulado = ""
    ruta_data = "data"
    if not os.path.exists(ruta_data):
        return ""

    for root, dirs, files in os.walk(ruta_data):
        for archivo in files:
            ruta_completa = os.path.join(root, archivo)
            try:
                # 1. PDFs
                if archivo.endswith(".pdf"):
                    reader = PdfReader(ruta_completa)
                    for pagina in reader.pages:
                        texto_acumulado += pagina.extract_text() + "\n"
                
                # 2. WORD (.docx)
                elif archivo.endswith(".docx"):
                    doc = Document(ruta_completa)
                    for para in doc.paragraphs:
                        texto_acumulado += para.text + "\n"
                
                # 3. EXCEL (.xlsx)
                elif archivo.endswith(".xlsx"):
                    df = pd.read_excel(ruta_completa)
                    texto_acumulado += f"\nDatos de Excel ({archivo}):\n" + df.to_string() + "\n"
                
                # 4. POWERPOINT (.pptx)
                elif archivo.endswith(".pptx"):
                    prs = Presentation(ruta_completa)
                    for slide in prs.slides:
                        for shape in slide.shapes:
                            if hasattr(shape, "text"):
                                texto_acumulado += shape.text + "\n"
                                
            except Exception as e:
                st.error(f"Error con {archivo}: {e}")
                
    return texto_acumulado

# Carga de archivos al iniciar la app
contexto_archivos = extraer_contenido_multiformato()

# Interfaz de Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Pregúntame sobre tus documentos o cualquier tema..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando información..."):
            try:
                instrucciones = f"""
                Eres EVANS.DA, un asistente híbrido avanzado.
                
                CONTEXTO DE TUS ARCHIVOS (PDF, Word, Excel, PPT):
                {contexto_archivos[:8000]} 
                
                INSTRUCCIONES:
                1. Si la respuesta está en los archivos, dales prioridad.
                2. Si es una pregunta general del mundo, responde con la verdad universal.
                3. Responde siempre en español.
                """

                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": instrucciones},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                )
                respuesta = chat_completion.choices[0].message.content
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
            except Exception as e:
                st.error(f"Error en la respuesta: {e}")