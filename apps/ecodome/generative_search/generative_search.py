
import os
import logging
from typing import Dict

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from google.generativeai.types import generation_types
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import Document
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain.chains.summarize import load_summarize_chain
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

from apps.tasks import get_task_result
from apps.ecodome.data_synthesis.knowledge.knowledge_base import KnowledgeBase
from apps.rpc_methods.utils import url_to_filename
from apps.tasks.google_search import async_google_image_search, async_product_google_search

def split_webpage(webpage_url: str):
    loader = WebBaseLoader(webpage_url)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(docs)
    return docs

def create_or_get_vectorstore(docs, gen_ai_result_id, embedding_model):
    index_path = os.path.join('./.runtimes/indexes', f'{gen_ai_result_id}_index')
    if os.path.exists(index_path):
        db = FAISS.load_local(f"{gen_ai_result_id}_index", embedding_model)

    db = FAISS.from_documents(docs, embedding_model)
    db.save_local(index_path)

    return db


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

GENERATIVE_SEARCH_QNA_PROMPT = """
You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.
Question: {question} 
Context: {context} 
Answer:
"""

def get_generative_search_chain(db, embedding_model, chat_model, query):
    prompt = ChatPromptTemplate.from_template(GENERATIVE_SEARCH_QNA_PROMPT)

    similar_embeddings=db.similarity_search(query)
    similar_embeddings=FAISS.from_documents(
        documents=similar_embeddings,
        embedding=embedding_model
    )

    retreiver = similar_embeddings.as_retriever()
    rag_chain = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
        | prompt
        | chat_model
        | StrOutputParser()
    )

    rag_chain_with_source = RunnableParallel(
        {"context": retreiver, "question": RunnablePassthrough()}
    ).assign(answer=rag_chain)

    return rag_chain_with_source


def generative_search(result_id, llm, embedding_model, search_term: str, image_url: str=None) -> Dict:
    subject, subject_link, webpage_url, image_results = None, None, None, None
    question, answer, response = None, None, None
    try:
        if image_url:
            # image_search_task = perform_image_search(image_url)
            image_search_result = async_google_image_search(image_url=image_url)
            subject, webpage_url, image_results = image_search_result
            if webpage_url:
                docs = split_webpage(embedding_model=embedding_model, webpage_url=webpage_url)
                db = create_or_get_vectorstore(docs=docs, embedding_model=embedding_model, gen_ai_result_id=result_id)
                rag_chain = get_generative_search_chain(chat_model=llm, embedding_model=embedding_model, db=db, query=search_term)
                QUERY = f"Explain the topic {search_term} in details. Explain in a point-wise manner."
                response = rag_chain.invoke(QUERY)
                question = response.get('question', '')
                answer = response.get('answer', '')
        else:
            # google_search_task = perform_product_google_search(search_term)
            google_search_result = async_product_google_search(search_term)
            QUERY_PROMPT = f"Using the context : {google_search_result}.\n Explain the topic {search_term} in details. Explain in a point-wise manner."
            output_parser = StrOutputParser()
            question = f"Explain {search_term}"
            llm = llm | output_parser
            answer = llm.invoke(QUERY_PROMPT)

        result = {
            'title': subject if subject else search_term,
            'question': question,
            'answer': answer,
            'images': image_results if image_results else [],
            'sources': [doc.metadata.get('source', '') for doc in response['context']] if response else [],
        }
        return result, subject_link
    except generation_types.BlockedPromptException as ex:
        raise Exception("Harmful or pornographic content not allowed")
    except Exception as ex:
        raise Exception("Error while performing generative search")