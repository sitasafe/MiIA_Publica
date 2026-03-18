import streamlit as st
import io, uuid, logging, os, shutil
import pandas as pd # <--- NUEVO: Motor para Excel
from datetime import datetime
from docx import Document
from pypdf import PdfReader
from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from duckduckgo_search import DDGS

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="EVANS.DA Multi-Doc", page_icon="📊", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource
def load_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

embeddings = load_embeddings()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. FUNCIÓN DE BÚSQUEDA WEB ---
def search_internet(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n\n".join(results)
    except Exception as e:
        return f"Error web: {e}"

# --- 3. EXTRACCIÓN DE TEXTO (AHORA CON EXCEL) ---
def extract_text(file):
    name = file.name.lower()
    try:
        file.seek(0)
        # LÓGICA PARA PDF
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file.read()))
            return "".join([p.extract_text() or "" for p in reader.pages[:50]])
        
        # LÓGICA PARA WORD
        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(file.read()))
            return "\n".join([p.text for p in doc.paragraphs])
        
        # LÓGICA PARA EXCEL (NUEVO)
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(file.read()))
            # Convertimos la tabla a un formato de texto que la IA entienda
            return f"Datos de la tabla {name}:\n" + df.to_string(index=False)
        
        # LÓGICA PARA CSV (NUEVO)
        elif name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file.read()))
            return f"Datos del CSV {name}:\n" + df.to_string(index=False)
            
        return ""
    except Exception as e:
        logging.error(f"Error en {name}: {e}")
        return ""

# --- 4. INTERFAZ LATERAL ---
with st.sidebar:
    st.header("📂 Base de Conocimiento")
    st.info("Formatos: PDF, DOCX, XLSX, CSV")
    uploaded_files = st.file_uploader("Sube tus archivos", accept_multiple_files=True, type=['pdf','docx','xlsx', 'csv'])
    
    if st.button("🔄 Indexar Todo"):
        path = f"./vectorstores/{st.session_state.user_id}"
        if os.path.exists(path): shutil.rmtree(path)
        
        if uploaded_files:
            texts, metas = [], []
            with st.spinner("Leyendo documentos y tablas..."):
                for f in uploaded_files:
                    t = extract_text(f)
                    if t:
                        chunks = [t[i:i+1500] for i in range(0, len(t), 1300)]
                        texts.extend(chunks)
                        metas.extend([{"source": f.name}] * len(chunks))
                
                if texts:
                    Chroma.from_texts(texts, embeddings, persist_directory=path, metadatas=metas)
                    st.success(f"¡{len(uploaded_files)} archivos listos!")

# --- 5. CHAT HÍBRIDO ---
st.title("🤖 EVANS.DA: Inteligencia Total 2026")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("Analiza mi Excel o pregunta sobre la actualidad...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        # A. Búsqueda Local (PDF/Word/Excel)
        path = f"./vectorstores/{st.session_state.user_id}"
        local_context = ""
        if os.path.exists(path) and os.listdir(path):
            vs = Chroma(persist_directory=path, embedding_function=embeddings)
            docs = vs.similarity_search(prompt, k=4)
            local_context = "\n---\n".join([f"Archivo: {d.metadata['source']}\n{d.page_content}" for d in docs])

        # B. Búsqueda Web
        with st.status("🌐 Consultando internet 2026..."):
            web_context = search_internet(prompt)

        # C. Generación
        fecha_hoy = datetime.now().strftime("%d de %B de %Y")
        sys_msg = (
            f"Hoy es {fecha_hoy}. Eres EVANS.DA. "
            "Cuentas con dos fuentes: <DOCS_LOCALES> (que pueden ser textos o tablas de Excel) "
            "y <WEB_2026>. Tu misión es dar respuestas exactas. "
            "Si el usuario te pide analizar datos numéricos del Excel, hazlo con precisión matemática."
        )
        
        payload = f"LOCAL:\n{local_context}\n\nWEB:\n{web_context}\n\nPREGUNTA: {prompt}"

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": payload}],
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
            st.error(f"Error: {e}")