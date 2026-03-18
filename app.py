import streamlit as st
from groq import Groq

# Configuración de página
st.set_page_config(page_title="EVANS.DA 🚀", page_icon="⚡")
st.title("🚀 EVANS.DA")
st.caption("Stack: Python + Groq Cloud + Streamlit")

# 1. Conexión segura con la llave que pegaste en Streamlit
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# 2. Historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. Entrada de usuario
if prompt := st.chat_input("Escribe tu duda sobre las Unidades 1-4..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 4. Respuesta de la IA
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                # AQUÍ ESTÁ EL CAMBIO IMPORTANTE:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile", 
                )
                respuesta = chat_completion.choices[0].message.content
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
            except Exception as e:
                st.error(f"Hubo un error con la API de Groq: {e}")