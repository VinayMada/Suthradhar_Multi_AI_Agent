import os
import pdfplumber
import requests
import openai
from bs4 import BeautifulSoup
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings 
from langchain_community.llms import OpenAI
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOpenAI

CHROMA_DB_DIR = "tmp/chroma_legal_db"
os.makedirs(CHROMA_DB_DIR, exist_ok=True)
openai.api_key = os.getenv("OPENAI_API_KEY")

# --------- Step 1: Extract Text from PDF ----------
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# --------- Step 2: Extract Text from URL ----------
def extract_text_from_url(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text(separator="\n")

# --------- Step 3: Store in ChromaDB ----------
def store_in_chroma(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    print("after text splitter")
    docs = [Document(page_content=chunk) for chunk in text_splitter.split_text(text)]
    print("afyer docs")

    embeddings = OpenAIEmbeddings()
    print("embeddings")
    db = Chroma.from_documents(documents=docs, embedding=embeddings, persist_directory=CHROMA_DB_DIR)
    print("db")
    db.persist()
    print("Done")
    return db

# --------- Step 4: Create Prompt to Extract Legal Arguments ----------
PROMPT_TEMPLATE = """You are a legal assistant. Carefully read the following document and extract:
1. Main legal issues.
2. Legal arguments presented by the parties.
3. Key judgments or rulings if any.
4. Statutory or constitutional provisions involved.

Document:
{context}

Respond with a structured summary of the above points.
"""

def create_rag_chain(chroma_db):
    retriever = chroma_db.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    prompt = PromptTemplate(input_variables=["context"], template=PROMPT_TEMPLATE)
    llm = ChatOpenAI(model="gpt-3.5-turbo")  # or "gpt-4"
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": prompt}
    )
    return chain

# --------- Step 5: Main Flow ----------
def main_function(source, is_pdf=True):
    print("[INFO] Extracting text...")
    text = extract_text_from_pdf(source) if is_pdf else extract_text_from_url(source)

    print("[INFO] Storing in ChromaDB...")
    db = store_in_chroma(text)

    print("[INFO] Creating RAG chain...")
    rag_chain = create_rag_chain(db)

    print("[INFO] Extracting legal arguments...")
    response = rag_chain.invoke("Extract legal issues and arguments from the document.")
    print("\n[RESULT]\n", response)