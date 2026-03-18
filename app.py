import streamlit as st
import io, uuid, logging, os, shutil
import pandas as pd
from datetime import datetime
from docx import Document # Para crear el reporte
from pypdf import PdfReader
from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from duckduckgo_search import DDGS

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="EVANS.DA Académico", page_icon="🎓", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_response" not in st.session_state:
    st.session_state.last_response = ""

@st.cache_resource
def load_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

embeddings = load_embeddings()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. FUNCIÓN DE BÚSQUEDA WEB (AMPLIADA A 10 FUENTES) ---
def search_internet(query):
    try:
        with DDGS() as ddgs:
            # Aumentamos max_results a 10 para una investigación más profunda
            results = [f"Fuente {i+1}: {r['body']}" for i, r in enumerate(ddgs.text(query, max_results=10))]
            return "\n\n".join(results)
    except Exception as e:
        return f"Error web: {e}"

# --- 3. FUNCIÓN PARA CREAR REPORTE WORD ---
def create_word_report(content, query):
    doc = Document()
    doc.add_heading('Reporte de Investigación EVANS.DA', 0)
    doc.add_paragraph(f'Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
    doc.add_heading('Consulta realizada:', level=1)
    doc.add_paragraph(query)
    doc.add_heading('Respuesta de la IA:', level=1)
    doc.add_paragraph(content)
    doc.add_paragraph('\n--- Fin del Reporte ---')
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 4. EXTRACCIÓN DE TEXTO ---
def extract_text(file):
    name = file.name.lower()
    try:
        file.seek(0)
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file.read()))
            return "".join([p.extract_text() or "" for p in reader.pages[:50]])
        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(file.read()))
            return "\n".join([p.text for p in doc.paragraphs])
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(file.read()))
            return f"Tabla {name}:\n{df.to_string(index=False)}"
        return ""
    except Exception as e:
        return ""

# --- 5. INTERFAZ LATERAL ---
with st.sidebar:
    st.header("📂 Panel de Control")
    uploaded_files = st.file_uploader("Sube archivos de Maestría", accept_multiple_files=True, type=['pdf','docx','xlsx'])
    
    if st.button("🔄 Indexar Documentos"):
        path = f"./vectorstores/{st.session_state.user_id}"
        if os.path.exists(path): shutil.rmtree(path)
        if uploaded_files:
            texts, metas = [], []
            with st.spinner("Procesando biblioteca..."):
                for f in uploaded_files:
                    t = extract_text(f)
                    if t:
                        chunks = [t[i:i+1500] for i in range(0, len(t), 1300)]
                        texts.extend(chunks)
                        metas.extend([{"source": f.name}] * len(chunks))
                if texts:
                    Chroma.from_texts(texts, embeddings, persist_directory=path, metadatas=metas)
                    st.success("¡Biblioteca lista!")

    st.divider()
    # BOTÓN DE DESCARGA
    if st.session_state.last_response:
        st.subheader("📄 Exportar Resultados")
        word_file = create_word_report(st.session_state.last_response, "Última consulta")
        st.download_button(
            label="📥 Descargar Reporte en Word",
            data=word_file,
            file_name=f"Reporte_EVANS_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

# --- 6. CHAT HÍBRIDO ---
st.title("🎓 EVANS.DA: Investigador de Maestría 2026")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("Escribe tu duda de investigación aquí...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        # A. Contexto Local (Biblioteca)
        path = f"./vectorstores/{st.session_state.user_id}"
        local_context = ""
        if os.path.exists(path) and os.listdir(path):
            vs = Chroma(persist_directory=path, embedding_function=embeddings)
            docs = vs.similarity_search(prompt, k=5)
            local_context = "\n---\n".join([f"Archivo: {d.metadata['source']}\n{d.page_content}" for d in docs])

        # B. Contexto Global (10 Fuentes)
        with st.status("🌐 Investigando en 10 fuentes de internet..."):
            web_context = search_internet(prompt)

        # C. Generación con Reglas de Verdad
        fecha_hoy = datetime.now().strftime("%d de %B de %Y")
        sys_msg = (
            f"Hoy es {fecha_hoy}. Eres EVANS.DA, un experto académico. "
            "REGLAS DE ORO: "
            "1. Usa EXCLUSIVAMENTE <DOCS_LOCALES> y <WEB_2026>. "
            "2. Cita siempre la fuente (nombre del archivo o 'Fuente Web'). "
            "3. Si no hay info, di 'No se encontró información'. NO inventes nada."
        )
        payload = f"LOCAL:\n{local_context}\n\nWEB:\n{web_context}\n\nPREGUNTA: {prompt}"

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": payload}],
                temperature=0.2, stream=True
            )
            for chunk in stream:
                content = getattr(chunk.choices[0].delta, "content", "")
                if content:
                    full_response += content
                    placeholder.markdown(full_response + "▌")
            
            placeholder.markdown(full_response)
            st.session_state.last_response = full_response # Guardamos para el Word
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            # Forzamos recarga para que aparezca el botón de descarga en el sidebar
            st.rerun() 
            
        except Exception as e:
            st.error(f"Error: {e}")