import os
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings

os.environ["GOOGLE_API_KEY"] = 'AIzaSyC5ncp8tP_wdN0u2PMZkil8B-XoSR6_Gvs'

embedding_model = GoogleGenerativeAIEmbeddings(
    google_api_key='AIzaSyC5ncp8tP_wdN0u2PMZkil8B-XoSR6_Gvs',
    model="models/embedding-001",
)
llm = ChatGoogleGenerativeAI(
    google_api_key='AIzaSyC5ncp8tP_wdN0u2PMZkil8B-XoSR6_Gvs',
    model="gemini-pro",
)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

loader = WebBaseLoader("https://en.wikipedia.org/wiki/Google_Docs")
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)
docs = splitter.split_documents(docs)
db = FAISS.from_documents(docs, embedding_model)
db.save_local(f"1234_index")
prompt = """ You need to answer the question in the sentence as same as in the  pdf content. . 
        Given below is the context and question of the user.
        context = {context}
        question = {question}
        if the answer is not in the pdf , answer "i donot know what the hell you are asking about"
"""
prompt = ChatPromptTemplate.from_template(prompt)


while True:
    query = str(input("Enter your query : "))
    if query:
        #getting only the chunks that are similar to the query for llm to produce the output
        similar_embeddings=db.similarity_search(query)
        similar_embeddings=FAISS.from_documents(documents=similar_embeddings, embedding=embedding_model)
        retreiver = similar_embeddings.as_retriever()
        rag_chain = (
            {"context": retreiver | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        response = rag_chain.invoke(query)
        print(response)