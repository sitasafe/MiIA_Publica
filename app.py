import streamlit as st
import requests

st.set_page_config(page_title="Mi IA - Stack Pro", page_icon="⚡")

st.title("🚀 EVANS.DA")
st.caption("Stack: Python + FastAPI + Ollama (Llama3)")

# Inicializar el historial de chat (como en ChatGPT)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Dibujar mensajes del historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input de usuario

if prompt := st.chat_input("Escribe tu pregunta aquí..."):
    # Guardar y mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Petición al Servidor (Backend)
    with st.chat_message("assistant"):
        with st.spinner("IA procesando..."):
            try:
                # Aquí conectamos con tu main.py de FastAPI
                response = requests.post(
                    "http://localhost:8000/preguntar",
                    json={"text": prompt}
                )
                
                if response.status_code == 200:
                    answer = response.json()["respuesta"]
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error("Error en la respuesta del servidor.")
            except Exception as e:
                st.error(f"Error: ¿Está corriendo el main.py? ({e})")