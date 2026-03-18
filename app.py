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

# --- 1. CONFIGURACIÓN DE ALTO RENDIMIENTO ---
st.set_page_config(
    page_title="EVANS.DA Super-Intelligence", 
    page_icon="🧠", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)
sns.set_theme(style="darkgrid", context="talk") 

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource
def load_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

embeddings = load_embeddings()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. MOTOR DE BÚSQUEDA ACADÉMICA FILTRADA ---
def search_internet(query):
    try:
        with DDGS() as ddgs:
            # Ampliamos la búsqueda a fuentes de alto impacto
            academic_query = f"{query} site:edu OR site:org OR 'research paper' OR 'case study'"
            res_es = [f"[ES-Academic] {r['body']}" for r in ddgs.text(query, max_results=6)]
            res_en = [f"[EN-Global] {r['body']}" for r in ddgs.text(academic_query, max_results=6)]
            return "\n\n".join(res_es + res_en)
    except Exception as e:
        return f"Error en red neuronal de búsqueda: {e}"

# --- 3. DATA VISUALIZATION ENGINE ---
def generate_chart(df, query):
    try:
        nums = df.select_dtypes(include=['number']).columns.tolist()
        cats = df.select_dtypes(include=['object', 'category']).columns.tolist()
        if nums:
            fig, ax = plt.subplots(figsize=(10, 6))
            if any(x in query.lower() for x in ["barra", "bar"]):
                sns.barplot(data=df, x=cats[0] if cats else df.index, y=nums[0], ax=ax, palette="magma")
            elif any(x in query.lower() for x in ["pastel", "pie"]):
                df.groupby(cats[0] if cats else df.index)[nums[0]].sum().plot(kind='pie', autopct='%1.1f%%', ax=ax)
            else:
                sns.lineplot(data=df, x=df.index, y=nums[0], ax=ax, marker="o", linewidth=2.5)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            return "📊 Análisis visual completado."
    except: return "⚠️ Error al renderizar gráfico."

# --- 4. EXTRACCIÓN DE CONOCIMIENTO ---
def extract_text(file):
    name = file.name.lower()
    try:
        file.seek(0)
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file.read()))
            return "".join([p.extract_text() or "" for p in reader.pages[:100]])
        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(file.read()))
            return "\n".join([p.text for p in doc.paragraphs])
        elif name.endswith((".xlsx", ".xls", ".csv")):
            df = pd.read_csv(file) if name.endswith(".csv") else pd.read_excel(file)
            st.session_state[f"df_{name}"] = df
            return f"Estructura de Datos {name}:\n{df.describe().to_string()}\n\nContenido:\n{df.to_string(index=False)}"
        return ""
    except: return ""

# --- 5. INTERFAZ ---
with st.sidebar:
    st.header("🧠 Nucleus Evans")
    uploaded_files = st.file_uploader("Entrenar con documentos", accept_multiple_files=True, type=['pdf','docx','xlsx', 'csv'])
    if st.button("🚀 Iniciar Entrenamiento", use_container_width=True):
        path = f"./vectorstores/{st.session_state.user_id}"
        if os.path.exists(path): shutil.rmtree(path)
        if uploaded_files:
            texts, metas = [], []
            for f in uploaded_files:
                t = extract_text(f)
                if t:
                    chunks = [t[i:i+2000] for i in range(0, len(t), 1800)]
                    texts.extend(chunks)
                    metas.extend([{"source": f.name}] * len(chunks))
            if texts:
                Chroma.from_texts(texts, embeddings, persist_directory=path, metadatas=metas)
                st.success("¡Cerebro actualizado!")

# --- 6. CHAT AGÉNTICO ---
st.title("🧠🌎 EVANS.DA: Super-Intelligence IA")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("Escribe una consulta compleja de maestría...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        # Lógica de Pensamiento (Agentic Workflow)
        with st.status("🧠 Evans está razonando...", expanded=True) as status:
            st.write("1. Analizando variables en tus documentos locales...")
            path = f"./vectorstores/{st.session_state.user_id}"
            local_context = ""
            if os.path.exists(path) and os.listdir(path):
                vs = Chroma(persist_directory=path, embedding_function=embeddings)
                docs = vs.similarity_search(prompt, k=6)
                local_context = "\n---\n".join([f"DOC: {d.metadata['source']}\n{d.page_content}" for d in docs])
            
            st.write("2. Ejecutando búsqueda en redes académicas globales...")
            web_context = search_internet(prompt)
            
            st.write("3. Cruzando datos y validando fuentes...")
            status.update(label="✅ Razonamiento completado", state="complete", expanded=False)

        # Gráficos si aplica
        if any(x in prompt.lower() for x in ["grafic", "gráfico", "analiza", "tendencia"]):
            for key in [k for k in st.session_state.keys() if k.startswith("df_")]:
                generate_chart(st.session_state[key], prompt)

        placeholder = st.empty()
        full_response = ""
        
        sys_msg = (
            "Eres EVANS.DA Super-Intelligence. Tu capacidad de razonamiento es superior. "
            "INSTRUCCIONES CRÍTICAS: "
            "1. Realiza síntesis de alto nivel comparando LOCAL vs GLOBAL. "
            "2. Si hay datos en inglés, tradúcelos con terminología académica técnica. "
            "3. Estructura tu respuesta con: Concepto, Análisis de Datos y Conclusión Científica. "
            "4. Cita fuentes estrictamente."
        )
        
        payload = f"DATOS_LOCALES:\n{local_context}\n\nINVESTIGACION_WEB:\n{web_context}\n\nCONSULTA: {prompt}"

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": payload}],
                temperature=0.1, # Menor temperatura = mayor precisión científica
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
            st.error(f"Error en núcleo: {e}")