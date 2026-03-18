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

# --- CSS PARA INTEGRAR EL BOTÓN "+" EN LA BARRA DE CHAT ---
st.markdown("""
    <style>
    /* Estilo para que el cargador de archivos parezca un botón circular '+' */
    section[data-testid="stFileUploadDropzone"] {
        padding: 0 !important;
        border: none !important;
        background-color: transparent !important;
        width: 40px !important;
        min-height: 40px !important;
    }
    .stFileUploadDropzone div div {
        display: none; /* Esconde el texto de 'drag and drop' */
    }
    .stFileUploadDropzone::before {
        content: '＋';
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        color: #555;
        border: 2px solid #ccc;
        border-radius: 50%;
        width: 35px;
        height: 35px;
        cursor: pointer;
    }
    /* Alineación de la barra inferior */
    .stChatInputContainer {
        padding-bottom: 20px;
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

# Historial de Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- ZONA DE ENTRADA ESTILO CHATGPT ---
# Usamos columnas muy desiguales para que el '+' esté pegado al chat
col_plus, col_chat = st.columns([0.1, 0.9])

with col_plus:
    # Este file_uploader ahora se ve como un botón '+' gracias al CSS arriba
    uploaded_files = st.file_uploader("", accept_multiple_files=True, label_visibility="collapsed")

with col_chat:
    prompt = st.chat_input("Pregunta lo que quieras...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Procesar todo el conocimiento (fijo y subido)
    contexto_total = ""
    if os.path.exists("data"):
        for root, dirs, files in os.walk("data"):
            for archivo in files:
                with open(os.path.join(root, archivo), "rb") as f:
                    contexto_total += procesar_archivo(archivo, f.read())
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            contexto_total += procesar_archivo(uploaded_file.name, uploaded_file.read())

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