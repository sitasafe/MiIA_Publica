import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

# 1. Configurar la base de datos local
client = chromadb.PersistentClient(path="./memoria_ia")
collection = client.get_or_create_collection(name="conocimiento_willan")

# 2. Cargar y procesar PDFs
def procesar_documentos():
    ruta_docs = "./data"
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    for archivo in os.listdir(ruta_docs):
        if archivo.endswith(".pdf"):
            print(f"Alimentando IA con: {archivo}...")
            loader = PyPDFLoader(os.path.join(ruta_docs, archivo))
            paginas = loader.load()
            
            # Dividir en trozos para que la IA no se atore
            trozos = text_splitter.split_documents(paginas)
            
            for i, trozo in enumerate(trozos):
                collection.add(
                    documents=[trozo.page_content],
                    ids=[f"{archivo}_{i}"]
                )
    print("¡IA Alimentada con éxito!")

if __name__ == "__main__":
    # Necesitas instalar pypdf y langchain: 
    # python -m pip install pypdf langchain_community langchain_text_splitters
    procesar_documentos()