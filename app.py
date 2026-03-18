import streamlit as st
import io, uuid, logging, os, shutil
from datetime import datetime
from docx import Document
from pypdf import PdfReader
from groq import Groq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# --- 1. CONFIGURACIÓN DE PÁGINA (DEBE SER LO PRIMERO) ---
st.set_page_config(page_title="EVANS.DA SaaS 🛡️", page_icon="🚀", layout="wide")

# --- 2. ESTADO DE SESIÓN ---
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- 4. CONFIGURACIÓN DE IA (GRATIS) ---
@st.cache_resource
def load_embeddings():
    # Modelo gratuito de HuggingFace que corre en el servidor de Streamlit
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

embeddings = load_embeddings()

# Cliente de Groq usando Secrets de Streamlit
api_key = st.secrets.get("GROQ_API_KEY")
if not api_key:
    st.error("⚠️ Error: Configura GROQ_API_KEY en los Secrets de Streamlit.")
    st.stop()
client = Groq(api_key=api_key)

# --- 5. UTILIDADES LÓGICAS ---
def extract_text(file):
    name = file.name.lower()
    content = ""
    try:
        file.seek(0)
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file.read()))
            for p in reader.pages[:50]: # Límite de 50 páginas por seguridad
                content += p.extract_text() or ""
        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(file.read()))
            for p in doc.paragraphs:
                content += p.text + "\n"
        return content
    except Exception as e:
        logging.error(f"Error extrayendo {file.name}: {e}")
        return ""

def get_vectorstore():
    path = f"./vectorstores/{st.session_state.user_id}"
    return Chroma(persist_directory=path, embedding_function=embeddings)

# --- 6. INTERFAZ LATERAL (GESTIÓN) ---
with st.sidebar:
    st.header("📂 Documentos de Investigación")
    uploaded_files = st.file_uploader("Sube PDF o DOCX", accept_multiple_files=True, type=['pdf','docx'])
    
    if st.button("🔄 Procesar e Indexar"):
        path = f"./vectorstores/{st.session_state.user_id}"
        if os.path.exists(path):
            shutil.rmtree(path)
        
        if uploaded_files:
            all_chunks, all_metas = [], []
            with st.spinner("Analizando documentos..."):
                for f in uploaded_files:
                    text = extract_text(f)
                    if text:
                        # Chunking simple: 1000 caracteres con solapamiento
                        chunks = [text[i:i+1000] for i in range(0, len(text), 900)]
                        all_chunks.extend(chunks)
                        all_metas.extend([{"source": f.name}] * len(chunks))
                
                if all_chunks:
                    vs = Chroma.from_texts(all_chunks, embeddings, 
                                          persist_directory=path, 
                                          metadatas=all_metas)
                    vs.persist()
                    st.success("¡Base de conocimiento actualizada!")
                else:
                    st.error("No se pudo extraer texto válido.")

# --- 7. INTERFAZ DE CHAT ---
st.title("🤖 EVANS.DA: Asistente de Maestría")
st.caption(f"ID Sesión Segura: {st.session_state.user_id}")

# Mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Haz una pregunta sobre tus documentos...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        # BÚSQUEDA RAG
        path = f"./vectorstores/{st.session_state.user_id}"
        context_text = "No hay documentos cargados. Responde con tu conocimiento general pero advierte al usuario."
        
        if os.path.exists(path) and os.listdir(path):
            vs = get_vectorstore()
            docs = vs.similarity_search(prompt, k=4)
            context_text = "\n\n".join([f"Origen: {d.metadata['source']}\nContenido: {d.page_content}" for d in docs])

        # CONFIGURACIÓN DE FECHA Y ROL
        fecha_actual = datetime.now().strftime("%d de %B de %Y")
        sys_msg = (
            f"Hoy es {fecha_actual}. Eres EVANS.DA, un asistente de investigación de maestría. "
            "Tu fuente de verdad absoluta es el contexto proporcionado en <CONTEXT>. "
            "Si la información está en el contexto, úsala. Si no está, responde: "
            "'Lo siento, no encuentro esa información en los documentos cargados'."
        )
        
        user_payload = f"<CONTEXT>\n{context_text}\n</CONTEXT>\n\nPREGUNTA: {prompt}"

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_payload}
                ],
                temperature=0.2,
                stream=True
            )

            for chunk in stream:
                content = getattr(chunk.choices[0].delta, "content", "")
                if content:
                    full_response += content
                    placeholder.markdown(full_response + "▌")
            
            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error("Error en la conexión con el motor de IA.")
            logging.error(f"Chat Error: {e}")