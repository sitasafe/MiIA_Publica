import streamlit as st
import io, uuid, logging, os, shutil
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from docx import Document
from pypdf import PdfReader
from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from duckduckgo_search import DDGS

# --- 1. CONFIGURACIÓN RESPONSIVE ---
st.set_page_config(
    page_title="EVANS.DA Research ia", 
    page_icon="🌎", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)
sns.set_theme(style="whitegrid", context="talk") 

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource
def load_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

embeddings = load_embeddings()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. FUNCIÓN DE BÚSQUEDA WEB (GLOBAL: EN + ES) ---
def search_internet(query):
    try:
        with DDGS() as ddgs:
            res_es = [f"[ES] {r['body']}" for r in ddgs.text(query, max_results=5)]
            res_en = [f"[EN] {r['body']}" for r in ddgs.text(f"{query} academic research paper MIT Harvard", max_results=5)]
            return "\n\n".join(res_es + res_en)
    except Exception as e:
        return f"Error web: {e}"

# --- 3. GENERADOR DE GRÁFICOS RESPONSIVE ---
def generate_chart(df, query):
    try:
        nums = df.select_dtypes(include=['number']).columns.tolist()
        cats = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        if nums:
            fig, ax = plt.subplots(figsize=(8, 5))
            if any(x in query.lower() for x in ["barra", "bar"]):
                sns.barplot(data=df, x=cats[0] if cats else df.index, y=nums[0], ax=ax, palette="viridis")
            elif any(x in query.lower() for x in ["pastel", "pie"]):
                df.groupby(cats[0] if cats else df.index)[nums[0]].sum().plot(kind='pie', autopct='%1.1f%%', ax=ax)
            else:
                sns.lineplot(data=df, x=df.index, y=nums[0], ax=ax, marker="o")
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            return "📊 Visualización generada con éxito."
    except:
        return "⚠️ No se pudo generar el gráfico automáticamente."

# --- 4. EXTRACCIÓN DE TEXTO (PDF, WORD, EXCEL, CSV) ---
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
            st.session_state[f"df_{name}"] = df
            return f"Datos de la tabla {name}:\n" + df.to_string(index=False)
        elif name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file.read()))
            st.session_state[f"df_{name}"] = df
            return f"Datos del CSV {name}:\n" + df.to_string(index=False)
        return ""
    except Exception as e:
        logging.error(f"Error en {name}: {e}")
        return ""

# --- 5. INTERFAZ LATERAL ---
with st.sidebar:
    st.header("📂 Base de Conocimiento")
    st.info("Formatos: PDF, DOCX, XLSX, CSV")
    uploaded_files = st.file_uploader("Sube tus archivos", accept_multiple_files=True, type=['pdf','docx','xlsx', 'csv'])
    
    if st.button("🔄 Indexar Todo", use_container_width=True):
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

# --- 6. CHAT HÍBRIDO (INTEGRACIÓN CORREGIDA) ---
st.title("🤖🌎 EVANS.DA: Inteligencia Total 2026")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): 
        st.markdown(msg["content"])

prompt = st.chat_input("Analiza mi Excel o investiga en Harvard/MIT...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): 
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # A. Lógica de Gráficos
        if any(x in prompt.lower() for x in ["grafic", "gráfico", "barra", "pastel", "pie"]):
            for key in [k for k in st.session_state.keys() if k.startswith("df_")]:
                generate_chart(st.session_state[key], prompt)

        placeholder = st.empty()
        full_response = ""
        
        # B. Búsqueda Local (RAG) - PARÉNTESIS BLINDADOS
        path = f"./vectorstores/{st.session_state.user_id}"
        local_context = ""
        if os.path.exists(path) and os.listdir(path):
            # Aquí se cerró correctamente el paréntesis de embeddings
            vs = Chroma(persist_directory=path, embedding_function=embeddings)
            docs = vs.similarity_search(prompt, k=4)
            local_context = "\n---\n".join([f"Archivo: {d.metadata['source']}\n{d.page_content}" for d in docs])

        # C. Búsqueda Web Global
        with st.status("🌐 Consultando internet global 2026..."):
            web_context = search_internet(prompt)

        # D. Generación con REGLAS ESTRICTAS
        fecha_hoy = datetime.now().strftime("%d de %B de %Y")
        sys_msg = (
            f"Hoy es {fecha_hoy}. Eres EVANS.DA. "
            "REGLAS ESTRICTAS DE VERDAD: "
            "1. Usa EXCLUSIVAMENTE <LOCAL> y <WEB>. "
            "2. Traduce información en inglés [EN] al español académico. "
            "3. Si no hay información, di: 'No cuento con esa información'. "
            "4. Cita siempre la fuente ([EN], [ES] o nombre de archivo)."
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
            st.error(f"Error de generación: {e}")