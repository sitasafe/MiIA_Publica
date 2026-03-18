import streamlit as st
import io, uuid, logging, os, shutil, re
import pandas as pd
import matplotlib.pyplot as plt # <--- NUEVO: Gráficos
import seaborn as sns # <--- NUEVO: Estética de gráficos
from datetime import datetime
from docx import Document
from pypdf import PdfReader
from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from duckduckgo_search import DDGS

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="EVANS.DA Global", page_icon="🌎", layout="wide")
sns.set_theme(style="whitegrid") # Estilo profesional para gráficos

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

# --- 2. INVESTIGACIÓN ACADÉMICA GLOBAL (INGLÉS + ESPAÑOL) ---
def search_global(query):
    context = ""
    try:
        with DDGS() as ddgs:
            # Buscamos en Español
            res_es = [f"[ES] {r['body']}" for r in ddgs.text(query, max_results=5)]
            # Buscamos en Inglés (Harvard/MIT/Academic)
            res_en = [f"[EN] {r['body']}" for r in ddgs.text(f"{query} academic research paper", max_results=5)]
            context = "\n\n".join(res_es + res_en)
            return context
    except Exception as e:
        return f"Error en búsqueda global: {e}"

# --- 3. GENERADOR DE GRÁFICOS ---
def generate_chart(df, query):
    try:
        # Buscamos columnas numéricas
        nums = df.select_dtypes(include=['number']).columns.tolist()
        cats = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        if len(nums) > 0:
            fig, ax = plt.subplots(figsize=(10, 6))
            if "barra" in query.lower() or "bar" in query.lower():
                df.plot(kind='bar', x=cats[0] if cats else None, y=nums[0], ax=ax, color='skyblue')
            elif "pastel" in query.lower() or "pie" in query.lower():
                df.groupby(cats[0] if cats else df.index)[nums[0]].sum().plot(kind='pie', autopct='%1.1f%%', ax=ax)
            else:
                df[nums[:2]].plot(kind='line', ax=ax)
            
            plt.xticks(rotation=45)
            st.pyplot(fig)
            return "📊 Gráfico generado exitosamente."
    except:
        return "⚠️ No pude generar el gráfico automáticamente. Intenta ser más específico con las columnas."

# --- 4. EXTRACCIÓN Y REPORTES ---
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
        elif name.endswith(".xlsx") or name.endswith(".csv"):
            df = pd.read_csv(file) if name.endswith(".csv") else pd.read_excel(file)
            st.session_state[f"df_{name}"] = df # Guardamos el dataframe para gráficos
            return f"Datos de {name}:\n{df.to_string(index=False)}"
        return ""
    except: return ""

# --- 5. INTERFAZ ---
with st.sidebar:
    st.header("📂 Laboratorio de Datos")
    uploaded_files = st.file_uploader("Sube PDF o Excel", accept_multiple_files=True, type=['pdf','docx','xlsx','csv'])
    
    if st.button("🔄 Procesar Conocimiento"):
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
                st.success("¡Global Intelligence Ready!")

# --- 6. CHAT HÍBRIDO ---
st.title("🤖🌎 EVANS.DA: Research & Data 2026")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("Analiza mi Excel con un gráfico o busca info en Harvard...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        # ¿Piden Gráfico?
        if any(x in prompt.lower() for x in ["grafic", "gráfico", "barra", "pastel", "pie chart"]):
            for key in st.session_state.keys():
                if key.startswith("df_"):
                    msg = generate_chart(st.session_state[key], prompt)
                    st.info(msg)

        # Investigación Global
        placeholder = st.empty()
        full_response = ""
        
        path = f"./vectorstores/{st.session_state.user_id}"
        local_context = ""
        if os.path.exists(path) and os.listdir(path):
            vs = Chroma(persist_directory=path, embedding_function=embeddings)
            docs = vs.similarity_search(prompt, k=5)
            local_context = "\n---\n".join([f"Archivo: {d.metadata['source']}\n{d.page_content}" for d in docs])

        with st.status("🌐 Investigando en fuentes globales (Harvard/MIT/Academic)..."):
            global_context = search_global(prompt)

        sys_msg = (
            f"Hoy es {datetime.now().strftime('%d de %B de %Y')}. Eres EVANS.DA Global AI. "
            "INSTRUCCIONES: "
            "1. Traduce cualquier información relevante en inglés al español académico. "
            "2. Compara fuentes locales con estándares internacionales. "
            "3. NO inventes datos. Cita la fuente: [EN] para inglés, [ES] para español."
        )
        payload = f"LOCAL:\n{local_context}\n\nGLOBAL_RESEARCH:\n{global_context}\n\nPREGUNTA: {prompt}"

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
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error: {e}")