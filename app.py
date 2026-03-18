# --- REEMPLAZA ESTE BLOQUE EN TU app.py ---
        
        # 1. Obtenemos la fecha exacta para el razonamiento
        fecha_hoy = datetime.now().strftime("%d de %B de %Y")
        
        # 2. Instrucciones Maestras Híbridas
        sys_msg = (
            f"Hoy es {fecha_hoy}. Eres EVANS.DA, una IA de investigación híbrida. "
            "TU LÓGICA DE TRABAJO: "
            "1. PRIORIDAD PDF: Si el usuario pregunta por 'mi archivo', 'mi tesis', 'los documentos' o temas específicos de los PDFs subidos, usa <DOCUMENTOS_PDF>. "
            "2. PRIORIDAD WEB: Si pregunta por noticias, precios, presidentes, leyes actuales o temas generales de 2024-2026, usa <INFORMACION_WEB>. "
            "3. MEZCLA: Si la pregunta requiere ambos (ej: 'compara mi tesis con la ley actual'), une ambas fuentes. "
            "4. IDIOMA: Responde siempre en español académico. Ignora definiciones irrelevantes de internet (como títulos nobiliarios) a menos que se te pida expresamente."
        )
        
        # 3. Payload de Contexto Unificado
        user_payload = f"""
        SISTEMA DE CONTEXTO HÍBRIDO:
        
        <DOCUMENTOS_PDF_LOCALES>
        {pdf_context if pdf_context.strip() else "El usuario no ha subido archivos aún."}
        </DOCUMENTOS_PDF_LOCALES>
        
        <INFORMACION_WEB_TIEMPO_REAL_2026>
        {web_context}
        </INFORMACION_WEB_TIEMPO_REAL_2026>
        
        PREGUNTA DEL ESTUDIANTE: {prompt}
        """