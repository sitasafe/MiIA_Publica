from groq import Groq
from datetime import datetime # 1. Agregamos el import de tiempo

# --- CLIENTE LLM (Gratis vía Groq) ---
api_key = st.secrets.get("GROQ_API_KEY")
if not api_key:
    st.error("⚠️ Falta GROQ_API_KEY en los Secrets.")
    st.stop()
client = Groq(api_key=api_key)

# ... (Todo tu código previo de extracción e interfaz se mantiene igual) ...

# --- CHAT ACTUALIZADO ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Escribe tu consulta académica...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        # --- BÚSQUEDA SEMÁNTICA (RAG) ---
        path = f"./vectorstores/{st.session_state.user_id}"
        context_text = "No se encontró información relevante en los documentos."
        
        if os.path.exists(path) and os.listdir(path):
            try:
                vs = get_vectorstore(st.session_state.user_id)
                docs = vs.similarity_search(prompt, k=5)
                context_text = "\n\n".join([f"--- Doc: {d.metadata['source']} ---\n{d.page_content}" for d in docs])
            except Exception as e:
                logging.error(f"Error recuperando contexto: {e}")

        # --- GENERACIÓN REAL CON LLAMA 3 (Groq) ---
        # 2. Obtenemos la fecha dinámicamente
        fecha_actual = datetime.now().strftime("%d de %B de %Y")
        
        # 3. Actualizamos el sys_msg con la instrucción de fecha y rigor
        sys_msg = (
            f"Hoy es {fecha_actual}. Eres EVANS.DA, un asistente de investigación de maestría. "
            "Tu fuente de verdad ABSOLUTA es el contexto proporcionado en <CONTEXT>. "
            "Prioriza los datos de 2026 si aparecen en el contexto. "
            "Si la respuesta no está en el contexto, di: 'Basado en los documentos subidos, no cuento con esa información'."
        )
        
        user_payload = f"<CONTEXT>\n{context_text}\n</CONTEXT>\n\nPREGUNTA DEL ESTUDIANTE: {prompt}"

        try:
            # Streaming para una UX fluida (SaaS Style)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_payload}
                ],
                temperature=0.2, # Bajamos un poco para evitar que invente
                stream=True
            )

            for chunk in completion:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    placeholder.markdown(full_response + "▌")
            
            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            logging.info(f"Respuesta generada para {st.session_state.user_id} el {fecha_actual}")

        except Exception as e:
            st.error("Hubo un problema con el motor de IA. Intenta de nuevo.")
            logging.error(f"Error en Groq API: {e}")