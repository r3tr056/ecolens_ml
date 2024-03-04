
import os
import logging
from hashlib import blake2b
from flask import jsonify, request, session, Blueprint

from langchain.storage import LocalFileStore
from langchain.embeddings import CacheBackedEmbeddings
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings

from apps.core.utils import api_key_required
from apps.ecodome.generative_search.generative_search import split_webpage, create_or_get_vectorstore, generative_search, get_generative_search_chain

gen_search_bp = Blueprint("gen_search", __name__)

embedding_store_path = os.path.join("./.runtime", os.getenv("EMBEDDING_CACHE_STORE", "embed_cache"))
embedding_cache_store = LocalFileStore(embedding_store_path)

embedding_model = GoogleGenerativeAIEmbeddings(
    google_api_key=os.getenv('GOOGLE_GEN_AI_API_KEY', ''),
    model="models/embedding-001",
)
cache_embedder = CacheBackedEmbeddings.from_bytes_store(
    embedding_model, embedding_cache_store, namespace=embedding_model.model,
)

chat_model = ChatGoogleGenerativeAI(
    google_api_key=os.getenv('GOOGLE_GEN_AI_API_KEY', ''),
    model="gemini-pro",
)

@gen_search_bp.post('/gensearch')
@api_key_required(required_role='user')
def generative_search_api():
    try:
        data = request.json
        search_term = data.get('search_term') 
        image_url = data.get('image_url', None)
        
        gen_ai_result_id = blake2b(search_term.encode()).hexdigest()[:64]
        result, webpage_url = generative_search(
            llm=chat_model,
            image_url=image_url,
            search_term=search_term,
            embedding_model=cache_embedder,
            result_id=gen_ai_result_id,
        )
        session['gen_ai_context'] = {
            'result_id': gen_ai_result_id,
            'webpage_url': webpage_url,
            'subject': result.get('title')
        }
        logging.debug(result)
        return jsonify({ 'result': result, 'result_id': gen_ai_result_id })
    except Exception as e:
        return jsonify({"error": f"Error occured : {e}"}), 500
    
@gen_search_bp.post('/ingest_docs')
@api_key_required(required_role='user')
def ingest_docs():
    try:
        data = request.json
        webpage_url = data.get('webpage_url')

        gen_ai_context = session.get('gen_ai_context')
        if gen_ai_context:
            result_id = gen_ai_context['result_id']
            webpage_url = gen_ai_context['webpage_url']
            if webpage_url:
                # ingest the webpage
                docs = split_webpage(embedding_model=cache_embedder, webpage_url=webpage_url)
                db = create_or_get_vectorstore(
                    docs=docs,
                    gen_ai_result_id=result_id,
                    embedding_model=cache_embedder,
                )
                session['gen_ai_context'] = {'db': db}

                return jsonify({"message": f"Created a vector db from the webpage {webpage_url}", "result_id": result_id}), 202
            return jsonify({"error":"No webpage url found to vectorize"}), 400
        return jsonify({"error": "Error occured while creating vectordb"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@gen_search_bp.post("/genchat")
@api_key_required(required_role='user')
def gen_chat():
    try:
        data = request.json
        query = data.get('query', '')

        gen_ai_context = session.get('gen_ai_context')
        if gen_ai_context:
            result_id = gen_ai_context['result_id']
            db = gen_ai_context['db']
            rag_chain = get_generative_search_chain(
                db=db,
                embedding_model=cache_embedder,
                chat_model=chat_model,
                query=query,
            )
            response = rag_chain.invoke({f"Answer this question : {query}"})
            result = { "question": response.get("question", ""), "answer": response.get("answer", "") }
            return jsonify({ "result": result, "result_id": result_id }), 200
        return jsonify({"error": "Error occured while generating followup responses. Run `/ingest_docs` first"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500