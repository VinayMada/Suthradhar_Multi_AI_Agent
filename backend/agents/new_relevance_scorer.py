import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
import os
from pinecone import Pinecone, ServerlessSpec
import uuid
import hashlib

# ---- Your API Keys ---

# ---- Pinecone Configuration ----
INDEX_NAME = "legal-documents"  # Change this to use an existing index
DIMENSION = 1536  # OpenAI embedding dimension

# ---- Utility Functions ----

def is_valid(url, domain):
    parsed = urlparse(url)
    return parsed.netloc == domain and parsed.scheme in ["http", "https"]

def extract_matching_descriptions(html, keyword):
    soup = BeautifulSoup(html, 'html.parser')
    matches = []

    for div in soup.find_all("div", class_="blog-post-description-style-font"):
        text = div.get_text(separator=" ", strip=True)
        if keyword.lower() in text.lower():
            matches.append(text)
            div_parent = div
            while div_parent:
                div_parent = div_parent.parent
                if div_parent is None:
                    break
                if div_parent.get("class") and "blog-post-category-link-hashtag-hover-color" in div_parent.get("class"):
                    print("[INFO] Matched Category Links:", div_parent.find_all('a'))
                    break

    for div in soup.find_all("div", class_="blog-post-title-font"):
        text = div.get_text(separator=" ", strip=True)
        if keyword.lower() in text.lower():
            matches.append(text)
            div_parent = div
            while div_parent:
                div_parent = div_parent.parent
                if div_parent is None:
                    break
                if div_parent.get("class") and "blog-post-category-link-hashtag-hover-color" in div_parent.get("class"):
                    print("[INFO] Matched Title Links:", div_parent.find_all('a'))
                    break

    return matches

def crawl_website(base_url, keyword, max_depth=2):
    visited = set()
    to_visit = [(base_url, 0)]
    domain = urlparse(base_url).netloc
    results = set()

    while to_visit:
        current_url, depth = to_visit.pop()
        if current_url in visited or depth > max_depth:
            continue

        try:
            print(f"[CRAWL] Visiting: {current_url} (Depth: {depth})")
            response = requests.get(current_url, timeout=10)
            visited.add(current_url)
            if response.status_code != 200:
                print(f"[WARN] Skipping {current_url} due to status code {response.status_code}")
                continue

            html = response.text
            matching_texts = extract_matching_descriptions(html, keyword)
            for match in matching_texts:
                results.add((current_url, match))

            # Queue internal links
            soup = BeautifulSoup(html, 'html.parser')
            for link_tag in soup.find_all('a', href=True):
                full_url = urljoin(current_url, link_tag['href'])
                if is_valid(full_url, domain) and full_url not in visited:
                    to_visit.append((full_url, depth + 1))

        except Exception as e:
            print(f"[ERROR] Failed to visit {current_url}: {e}")
            continue

    print(f"[CRAWL] Total matched entries (titles/descriptions): {len(results)}")
    return list(results)

def initialize_pinecone():
    """Initialize Pinecone client and connect to existing index or create if possible"""
    print("[PINECONE] Initializing Pinecone...")
    
    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    
    # List existing indexes
    existing_indexes = pc.list_indexes().names()
    print(f"[PINECONE] Existing indexes: {existing_indexes}")
    
    if INDEX_NAME not in existing_indexes:
        if len(existing_indexes) >= 5:
            print(f"[PINECONE] ERROR: You have reached the maximum number of indexes (5).")
            print(f"[PINECONE] Available indexes: {existing_indexes}")
            print(f"[PINECONE] Please either:")
            print(f"[PINECONE] 1. Delete an unused index from your Pinecone dashboard")
            print(f"[PINECONE] 2. Or change INDEX_NAME to use an existing index")
            print(f"[PINECONE] 3. Or upgrade your Pinecone plan")
            
            # Ask user to choose an existing index
            if existing_indexes:
                print(f"\n[PINECONE] Would you like to use an existing index?")
                print(f"[PINECONE] Available indexes: {existing_indexes}")
                print(f"[PINECONE] Using the first available index: {existing_indexes[0]}")
                index_to_use = existing_indexes[0]
            else:
                raise Exception("No existing indexes available and cannot create new one")
        else:
            print(f"[PINECONE] Creating new index: {INDEX_NAME}")
            try:
                pc.create_index(
                    name=INDEX_NAME,
                    dimension=DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                # Wait for index to be ready
                print("[PINECONE] Waiting for index to be ready...")
                time.sleep(10)
                index_to_use = INDEX_NAME
            except Exception as e:
                print(f"[PINECONE] Failed to create index: {e}")
                if existing_indexes:
                    print(f"[PINECONE] Falling back to existing index: {existing_indexes[0]}")
                    index_to_use = existing_indexes[0]
                else:
                    raise e
    else:
        print(f"[PINECONE] Using existing index: {INDEX_NAME}")
        index_to_use = INDEX_NAME
    
    # Connect to index
    index = pc.Index(index_to_use)
    print(f"[PINECONE] Successfully connected to index: {index_to_use}")
    return index

def generate_id(text, url):
    """Generate a unique ID for a document chunk"""
    content = f"{url}_{text[:100]}"
    return hashlib.md5(content.encode()).hexdigest()

def build_vectorstore_from_urls(url_list, index):
    """Load documents from URLs and store in Pinecone"""
    print(f"\n[BUILD] Loading documents from {len(url_list)} URLs...")
    
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    
    all_docs = []
    for url in url_list:
        try:
            print(f"[BUILD] Fetching: {url}")
            loader = WebBaseLoader(url)
            docs_from_url = loader.load()
            all_docs.extend(docs_from_url)
            print(f"[BUILD] Loaded {len(docs_from_url)} docs from {url}")
        except Exception as e:
            print(f"[ERROR] Failed to load {url}: {e}")
            continue

    if not all_docs:
        print("[ERROR] No documents loaded. Exiting.")
        return None

    print(f"[BUILD] Total loaded documents: {len(all_docs)}")
    print("[BUILD] Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=200)
    doc_splits = text_splitter.split_documents(all_docs)
    print(f"[BUILD] Total chunks created: {len(doc_splits)}")

    print("[BUILD] Creating embeddings and storing in Pinecone...")
    
    # Process documents in batches
    batch_size = 100
    total_batches = (len(doc_splits) + batch_size - 1) // batch_size
    
    for i in range(0, len(doc_splits), batch_size):
        batch = doc_splits[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"[BUILD] Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")
        
        vectors_to_upsert = []
        for doc in batch:
            try:
                # Generate embedding
                embedding = embeddings.embed_query(doc.page_content)
                
                # Create unique ID
                doc_id = generate_id(doc.page_content, doc.metadata.get('source', 'unknown'))
                
                # Prepare vector for upsert
                vector_data = {
                    'id': doc_id,
                    'values': embedding,
                    'metadata': {
                        'text': doc.page_content,
                        'source': doc.metadata.get('source', 'unknown'),
                        'chunk_length': len(doc.page_content)
                    }
                }
                vectors_to_upsert.append(vector_data)
                
            except Exception as e:
                print(f"[ERROR] Failed to process document chunk: {e}")
                continue
        
        # Upsert batch to Pinecone
        if vectors_to_upsert:
            try:
                index.upsert(vectors=vectors_to_upsert)
                print(f"[BUILD] Successfully upserted {len(vectors_to_upsert)} vectors")
            except Exception as e:
                print(f"[ERROR] Failed to upsert batch: {e}")
        
        # Small delay between batches
        time.sleep(1)

    print("[BUILD] Vector store built and stored in Pinecone successfully.")
    return index

def get_top_k_chunks(index, keyword, k=5):
    """Query Pinecone for top k similar chunks"""
    print(f"\n[SEARCH] Querying top {k} chunks for keyword: '{keyword}'")
    
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    query_vector = embeddings.embed_query(keyword)
    
    # Query Pinecone
    try:
        results = index.query(
            vector=query_vector,
            top_k=k,
            include_metadata=True
        )
        
        print(f"[SEARCH] Top {k} results:")
        top_results = []
        
        for i, match in enumerate(results.matches):
            url = match.metadata.get("source", "Unknown URL")
            content = match.metadata.get("text", "No content")[:500] + "..."
            score = match.score
            
            top_results.append((url, content, score))
            
            print(f"\nResult {i+1}:")
            print(f"URL: {url}")
            print(f"Score: {score:.4f}")
            print(f"Content: {content}")
        
        return top_results
        
    except Exception as e:
        print(f"[ERROR] Failed to query Pinecone: {e}")
        return []

# ---- MAIN EXECUTION ----

def main_function_for_relevance(keyword):
    start_url = "https://www.ijllr.com/papers"
    
    # Initialize Pinecone
    try:
        pinecone_index = initialize_pinecone()
    except Exception as e:
        print(f"[ERROR] Failed to initialize Pinecone: {e}")
        exit(1)
    
    print("[MAIN] Starting crawl...")
    results = crawl_website(start_url, keyword=keyword, max_depth=5)

    website_urls = list(set(url for url, text in results))
    print(f"[MAIN] Unique URLs found: {len(website_urls)}")
    
    if website_urls:
        # Build vector store in Pinecone
        build_vectorstore_from_urls(website_urls, pinecone_index)
        
        # Query for top chunks
        top_chunks = get_top_k_chunks(pinecone_index, keyword=keyword, k=5)
        
        print("\n[MAIN] Final Top Chunks:")
        for i, (url, content, score) in enumerate(top_chunks):
            print(f"\n{i+1}. URL: {url}\nScore: {score:.4f}\nContent: {content}")
        
        print(top_chunks)
        return top_chunks
    else:
        print("[MAIN] No URLs found to process.")
        return []
    
