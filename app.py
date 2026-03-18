import streamlit as st
from groq import Groq
from pypdf import PdfReader
from docx import Document

# 1. Configuración de página
st.set_page_config(page_title="EVANS.DA 🚀", page_icon="🤖", layout="wide")

# --- ESTILO ---
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
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 EVANS.DA")
    if st.button("🗑️ Borrar Historial"):
        st.session_state.messages = []
        st.rerun()

# --- LÓGICA DE ARCHIVOS ---
def leer_archivo(f):
    content = ""
    if f.name.endswith(".pdf"):
        pdf = PdfReader(f)
        for page in pdf.pages: content += (page.extract_text() or "")
    elif f.name.endswith(".docx"):
        doc = Document(f)
        for p in doc.paragraphs: content += p.text + "\n"
    return content

# --- INTERFAZ ---
st.title("🤖 Asistente EVANS.DA")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

with st.container():
    col1, col2 = st.columns([0.1, 0.9])
    with col1:
        opciones = st.popover("➕")
        with opciones:
            files = st.file_uploader("Adjuntar PDF/Word", accept_multiple_files=True)
    with col2:
        prompt = st.chat_input("Escribe tu consulta aquí...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    contexto = ""
    if files:
        for f in files: contexto += leer_archivo(f)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            res = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Eres EVANS.DA, un asistente experto."},
                    {"role": "user", "content": f"Contexto: {contexto}\n\nPregunta: {prompt}"}
                ],
                model="llama-3.3-70b-versatile",
            ).choices[0].message.content
            
            st.markdown(res)
            st.session_state.messages.append({"role": "assistant", "content": res})