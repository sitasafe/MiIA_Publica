import streamlit as st
from groq import Groq
import os
from pypdf import PdfReader # <-- Cambiado para usar pypdf

# Configuración visual
st.set_page_config(page_title="EVANS.DA Híbrida 🚀", page_icon="🎓")
st.title("🚀 EVANS.DA: Inteligencia Híbrida")
st.caption("Conocimiento General + Tus PDFs de Maestría")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- FUNCIÓN PARA LEER TODOS LOS PDFS EN LA CARPETA DATA ---
def extraer_texto_pdfs():
    texto_acumulado = ""
    ruta_data = "data"
    if os.path.exists(ruta_data):
        for archivo in os.listdir(ruta_data):
            if archivo.endswith(".pdf"):
                try:
                    reader = PdfReader(os.path.join(ruta_data, archivo))
                    for pagina in reader.pages:
                        texto = pagina.extract_text()
                        if texto:
                            texto_acumulado += texto + "\n"
                except Exception as e:
                    st.error(f"Error leyendo {archivo}: {e}")
    return texto_acumulado

# Cargamos el contenido de tus documentos
contenido_pdfs = extraer_texto_pdfs()

# Historial de Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de usuario
if prompt := st.chat_input("Pregúntame lo que sea..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en documentos y cerebro general..."):
            try:
                # INSTRUCCIONES HÍBRIDAS
                instrucciones = f"""
                Eres EVANS.DA, una IA de conocimiento general con acceso a documentos específicos del usuario.
                
                CONTEXTO DE MIS DOCUMENTOS:
                {contenido_pdfs[:8000]} 
                
                REGLAS:
                1. Si la pregunta se responde con el CONTEXTO de los PDFs, úsalo prioritariamente.
                2. Si la pregunta es sobre cualquier otro tema del mundo, responde con la VERDAD universal.
                3. Responde siempre en español de forma profesional.
                """

                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": instrucciones},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                )
                
                respuesta = chat_completion.choices[0].message.content
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
                
            except Exception as e:
                st.error(f"Hubo un error: {e}")