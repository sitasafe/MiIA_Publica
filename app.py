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
    page_title="EVANS.DA Global", 
    page_icon="🌎", 
    layout="wide", # Usa todo el ancho disponible
    initial_sidebar_state="collapsed" # Colapsado en móvil para dar espacio
)
sns.set_theme(style="whitegrid", context="talk") # "talk" hace los textos del gráfico más grandes y legibles

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource
def load_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

embeddings = load_embeddings()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. INVESTIGACIÓN GLOBAL ---
def search_global(query):
    try:
        with DDGS() as ddgs:
            res_es = [f"[ES] {r['body']}" for r in ddgs.text(query, max_results=4)]
            res_en = [f"[EN] {r['body']}" for r in ddgs.text(f"{query} academic research MIT Harvard", max_results=4)]
            return "\n\n".join(res_es + res_en)
    except: return "Error en búsqueda global."

# --- 3. GENERADOR DE GRÁFICOS RESPONSIVE ---
def generate_chart(df, query):
    try:
        nums = df.select_dtypes(include=['number']).columns.tolist()
        cats = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        if nums:
            # Creamos el gráfico con un tamaño base adaptable
            fig, ax = plt.subplots(figsize=(8, 5))
            if any(x in query.lower() for x in ["barra", "bar"]):
                sns.barplot(data=df, x=cats[0] if cats else df.index, y=nums[0], ax=ax, palette="viridis")
            elif any(x in query.lower() for x in ["pastel", "pie"]):
                df.groupby(cats[0] if cats else df.index)[nums[0]].sum().plot(kind='pie', autopct='%1.1f%%', ax=ax)
            else:
                sns.lineplot(data=df, x=df.index, y=nums[0], ax=ax, marker="o")
            
            plt.xticks(rotation=45)
            plt.tight_layout() # Evita que los textos se corten
            st.pyplot(fig, use_container_width=True) # <--- CLAVE PARA RESPONSIVE
            return "📊 Visualización adaptada generada."
    except: return "⚠️ No pude procesar el gráfico."

# --- 4. EXTRACCIÓN ---
def extract_text(file):
    name = file.name.lower()
    try:
        file.seek(0)
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file.read()))
            return "".join([p.extract_text() or "" for p in reader.pages[:50]])
        elif name.endswith((".xlsx", ".csv")):
            df = pd.read_csv(file) if name.endswith(".csv") else pd.read_excel(file)
            st.session_state[f"df_{name}"] = df
            return f"Datos de {name}:\n{df.head(20).to_string(index=False)}"
        return ""
    except: return ""

# --- 5. INTERFAZ ---
with st.sidebar:
    st.header("📂 Datos de Maestría")
    uploaded_files = st.file_uploader("Sube PDF o Excel", accept_multiple_files=True, type=['pdf','docx','xlsx','csv'])
    
    if st.button("🔄 Indexar Todo", use_container_width=True):
        path = f"./vectorstores/{st.session_state.user_id}"
        if os.path.exists(path): shutil.rmtree(path)
        if uploaded_files:
            texts, metas = [], []
            for f in uploaded_files:
                t = extract_text(f)
                if t:
                    chunks = [t[i:i+1500] for i in range(0, len(t), 1300)]
                    texts.extend(chunks)
                    metas.extend([{"source": f.name}] * len(chunks))
            if texts:
                Chroma.from_texts(texts, embeddings, persist_directory=path, metadatas=metas)
                st.success("¡Conocimiento Listo!")

# --- 6. CHAT ---
st.title("🤖🌎 EVANS.DA: Global AI")

# Contenedor para el historial de chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Pregunta algo o pide un gráfico...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        # Lógica de Gráficos
        if any(x in prompt.lower() for x in ["grafic", "gráfico", "barra", "pastel"]):
            for key in [k for k in st.session_state.keys() if k.startswith("df_")]:
                st.write(f"Analizando: {key.replace('df_', '')}")
                generate_chart(st.session_state[key], prompt)

        # Lógica de Respuesta Híbrida
        placeholder = st.empty()
        full_response = ""
        
        with st.status("🔍 Investigando globalmente...", expanded=False):
            global_context = search_global(prompt)
            # RAG Local
            path = f"./vectorstores/{st.session_state.user_id}"
            local_context = ""
            if os.path.exists(path) and os.listdir(path):
                vs = Chroma(persist_directory=path, embedding_function=