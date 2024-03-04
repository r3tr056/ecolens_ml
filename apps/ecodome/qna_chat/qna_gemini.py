import os

import google.generativeai as google_genai

from flask import Flask, jsonify, request, session

from langchain.globals import set_llm_cache
from langchain.cache import SQLiteCache
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import SQLChatMessageHistory
from langchain.vectorstores.faiss import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

app = Flask(__name__)

google_genai.configure(api_key=os.getenv("GOOLE_API_KEY"))
set_llm_cache(SQLiteCache(database_path='.qna_response.db'))

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vectorstore(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embeddings-001")
    vectorstore = FAISS.from_texts(text_chunks, embedding=embeddings)
    vectorstore.save_local("faiss_index")

def get_conversational_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ]
    )
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    chain_with_history = RunnableWithMessageHistory(
        chain,
        session['qa_session'],
        input_messages_key="question",
        history_messages_key="history",
    )
    return chain_with_history


@app.route('/start', method=['POST'])
def start_chat():
    data = request.json
    if 'user_id' in data:
        user_id = data['user_id']
        session['user_id'] = user_id
        session['qa_session'] = SQLChatMessageHistory(session_id=user_id)
        return jsonify({"message": f"User {user_id} started chat."})
    return jsonify({"error": "Invalid request. Please provide a 'user_id' field in the request"})

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    if 'question' in data:
        question = data['question']
        chain = get_conversational_chain()
        response = chain.invoke({"question": question}).content
        return jsonify({"response": response})
    return jsonify({"error": "Invalid request. Please provide a 'question' field in the request."})



