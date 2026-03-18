import streamlit as st
import io, uuid, logging, os, shutil
from datetime import datetime
from docx import Document
from pypdf import PdfReader
from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from duckduckgo_search import DDGS

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="EVANS.DA", page_icon="🌐", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource
def load_embeddings():
    # Modelo ligero y rápido para Streamlit Cloud
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

embeddings = load_embeddings()

# Verificación de API Key
if "GROQ_API_KEY" not in st.secrets:
    st.error("⚠️ Falta GROQ_API_KEY en los Secrets de Streamlit.")
    st.stop()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. FUNCIÓN DE BÚSQUEDA EN INTERNET ---
def search_internet(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n\n".join(results)
    except Exception as e:
        logging.error(f"Error búsqueda web: {e}")
        return "No se pudo obtener información de la web en este momento."

# --- 3. EXTRACCIÓN DE TEXTO ---
def extract_text(file):
    content = ""
    try:
        file.seek(0)
        if file.name.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file.read()))
            for p in reader.pages[:50]:
                content += p.extract_text() or ""
        elif file.name.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file.read()))
            for p in doc.paragraphs:
                content += p.text + "\n"
        return content
    except Exception as e:
        logging.error(f"Error en {file.name}: {e}")
        return ""

# --- 4. INTERFAZ LATERAL ---
with st.sidebar:
    st.header("📂 Documentos Locales")
    uploaded_files = st.file_uploader("Sube archivos (PDF/DOCX)", accept_multiple_files=True, type=['pdf','docx'])
    
    if st.button("🔄 Indexar Documentos"):
        path = f"./vectorstores/{st.session_state.user_id}"
        if os.path.exists(path):
            shutil.rmtree(path)
        
        if uploaded_files:
            texts, metas = [], []
            with st.spinner("Procesando archivos..."):
                for f in uploaded_files:
                    t = extract_text(f)
                    if t:
                        chunks = [t[i:i+1000] for i in range(0, len(t), 900)]
                        texts.extend(chunks)
                        metas.extend([{"source": f.name}] * len(chunks))
                
                if texts:
                    Chroma.from_texts(texts, embeddings, persist_directory=path, metadatas=metas)
                    st.success("¡Base de conocimientos lista!")
                else:
                    st.warning("No se pudo extraer texto de los archivos.")

# --- 5. CHAT HÍBRIDO ---
st.title("🤖 EVANS.DA: Inteligencia Híbrida 2026")

# Mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Pregunta lo que quieras...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        # A. Búsqueda en PDF (Contexto Local)
        path = f"./vectorstores/{st.session_state.user_id}"
        pdf_context = ""
        if os.path.exists(path) and os.listdir(path):
            vs = Chroma(persist_directory=path, embedding_function=embeddings)
            docs = vs.similarity_search(prompt, k=3)
            pdf_context = "\n".join([f"Fuente: {d.metadata['source']}\nContenido: {d.page_content}" for d in docs])

        # B. Búsqueda en Internet (Contexto Tiempo Real)
        with st.status("🌐 Consultando fuentes de marzo 2026..."):
            web_context = search_internet(prompt)

        # C. Generación Final con Lógica Híbrida
        fecha_hoy = datetime.now().strftime("%d de %B de %Y")
        
        sys_msg = (
            f"Hoy es {fecha_hoy}. Eres EVANS.DA, una IA de investigación híbrida avanzada. "
            "TU LÓGICA DE TRABAJO: "
            "1. PRIORIDAD PDF: Si el usuario pregunta por sus archivos o temas específicos cargados, usa <DOCUMENTOS_PDF_LOCALES>. "
            "2. PRIORIDAD WEB: Si pregunta por actualidad, noticias o datos generales de 2026, usa <INFORMACION_WEB_2026>. "
            "3. MEZCLA: Si la pregunta requiere ambos, integra las fuentes. "
            "4. IDIOMA: Responde en español académico. Ignora definiciones irrelevantes de internet."
        )
        
        user_payload = f"""
        SISTEMA DE CONTEXTO HÍBRIDO:
        
        <DOCUMENTOS_PDF_LOCALES>
        {pdf_context if pdf_context.strip() else "No hay documentos cargados."}
        </DOCUMENTOS_PDF_LOCALES>
        
        <INFORMACION_WEB_2026>
        {web_context}
        </INFORMACION_WEB_2026>
        
        PREGUNTA: {prompt}
        """

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_payload}
                ],
                temperature=0.3,
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
            st.error(f"Error en el motor de IA: {e}")