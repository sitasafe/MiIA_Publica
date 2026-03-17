import os
from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

# Cargar la llave desde el archivo .env
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI(title="IA Pública de Willan")

class Query(BaseModel):
    text: str

@app.post("/preguntar")
async def ask_ia(query: Query):
    try:
        # Llama 3 en la nube de Groq (Ultra rápido)
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": query.text}],
            model="llama3-8b-8192",
        )
        return {"respuesta": chat_completion.choices[0].message.content}
    except Exception as e:
        return {"respuesta": f"Error en la conexión: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)