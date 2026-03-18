import streamlit as st
from groq import Groq

# Configuración de página
st.set_page_config(page_title="EVANS.DA 🚀", page_icon="⚡")
st.title("🚀 EVANS.DA")
st.caption("Stack: Python + Groq Cloud + Streamlit")

# 1. Conexión segura con la llave de Streamlit
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

    # 4. Respuesta de la IA con ENTRENAMIENTO
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                # --- AQUÍ DEFINES LAS INSTRUCCIONES (EL ENTRENAMIENTO) ---
                instrucciones = """
                Eres EVANS.DA, un asistente experto en seguridad y prevención. 
                Tu objetivo es ayudar a los estudiantes con las Unidades 1 a 4.
                Responde siempre en español, de forma profesional y educativa. 
                Si no sabes algo, admítelo, pero intenta guiar al usuario.
                """

                # Enviamos las instrucciones en el rol de "system"
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": instrucciones}, # El entrenamiento
                        {"role": "user", "content": prompt}            # La pregunta
                    ],
                    model="llama-3.3-70b-versatile", 
                )
                
                respuesta = chat_completion.choices[0].message.content
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
                
            except Exception as e:
                st.error(f"Hubo un error con la API de Groq: {e}")