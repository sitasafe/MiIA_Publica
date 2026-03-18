import streamlit as st
import io, uuid, logging, os, shutil
from datetime import datetime
from docx import Document
from pypdf import PdfReader
from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from duckduckgo_search import DDGS # <--- BUSCADOR EN VIVO

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="EVANS.DA", page_icon="🌐", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource
def load_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

embeddings = load_embeddings()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. FUNCIÓN DE BÚSQUEDA EN INTERNET ---
def search_internet(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n\n".join(results)
    except Exception as e:
        return f"Error en búsqueda web: {e}"

# --- 3. EXTRACCIÓN Y LÓGICA RAG ---
def extract_text(file):
    content = ""
    try:
        file.seek(0)
        if file.name.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file.read()))
            for p in reader.pages[:50]: content += p.extract_text() or ""
        elif file.name.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file.read()))
            for p in doc.paragraphs: content += p.text + "\n"
        return content
    except: return ""

# --- 4. INTERFAZ LATERAL ---
with st.sidebar:
    st.header("📂 Documentos Locales")
    uploaded_files = st.file_uploader("Sube archivos", accept_multiple_files=True, type=['pdf','docx'])
    if st.button("🔄 Indexar"):
        path = f"./vectorstores/{st.session_state.user_id}"
        if os.path.exists(path): shutil.rmtree(path)
        if uploaded_files:
            texts, metas = [], []
            for f in uploaded_files:
                t = extract_text(f)
                if t:
                    chunks = [t[i:i+1000] for i in range(0, len(t), 900)]
                    texts.extend(chunks)
                    metas.extend([{"source": f.name}] * len(chunks))
            if texts:
                Chroma.from_texts(texts, embeddings, persist_directory=path, metadatas=metas)
                st.success("PDFs listos.")

# --- 5. CHAT HÍBRIDO ---
st.title("🤖 EVANS.DA: Inteligencia Híbrida 2026")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("Pregunta sobre tus PDFs o sobre la actualidad de 2026...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        # A. BUSCAR EN PDF (Contexto Local)
        path = f"./vectorstores/{st.session_state.user_id}"
        pdf_context = ""
        if os.path.exists(path) and os.listdir(path):
            vs = Chroma(persist_directory=path, embedding_function=embeddings)
            docs = vs.similarity_search(prompt, k=3)
            pdf_context = "\n".join([d.page_content for d in docs])

        # B. BUSCAR EN INTERNET (Contexto Global 2026)
        with st.status("🌐 Consultando fuentes de marzo 2026..."):
            web_context = search_internet(prompt)

        # C. GENERACIÓN FINAL
        fecha_hoy = datetime.now().strftime("%d de %B de %Y")
        sys_msg = (
            f"Hoy es {fecha_hoy}. Eres EVANS.DA, una IA híbrida avanzada. "
            "INSTRUCCIONES DE RESPUESTA: "
            "1. Si la respuesta está en los <DOCUMENTOS_PDF>, dala basándote en ellos. "
            "2. Si la pregunta es sobre actualidad o no está en los PDFs, usa la <INFORMACION_WEB>. "
            "3. No menciones que tu corte es 2023. Actúa con datos del presente (2026). "
            "4. Sé preciso, académico y directo."
        )
        
        full_context = f"""
        <DOCUMENTOS_PDF>
        {pdf_context if pdf_context else "No hay PDFs cargados."}
        </DOCUMENTOS_PDF>
        
        <INFORMACION_WEB>
        {web_context}
        </INFORMACION_WEB>
        """

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": f"CONTEXTO:\n{full_context}\n\nPREGUNTA: {prompt}"}
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
            st.error(f"Error: {e}")