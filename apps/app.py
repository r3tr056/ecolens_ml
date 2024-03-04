from dotenv import load_dotenv

from apps.core.pubsub.client import PubSubRPCClient

load_dotenv()

import os
import logging
from celery import Celery, Task
from flask import Flask, current_app
from werkzeug.middleware.proxy_fix import ProxyFix
from langchain.graphs.neo4j_graph import Neo4jGraph

from apps.core.db import db_session
from apps.api.generative_search import gen_search_bp
from apps.ecodome.data_synthesis.knowledge.knowledge_base import KnowledgeBase

# def create_and_return_greeting(tx, message):
#     result = tx.run("CREATE (a:Greeting) "
#         "SET a.message = $message "
#         "RETURN a.message + ', from node ' + id(a)", message=message)
#     return result.single()[0]

# def create_knowledge_base(app, bootstrap_knowledge_dir):
#     """ Creates an instance of knowledge base """
#     try:
#         n4j_graph = Neo4jGraph(
#             url=os.getenv('NEO4J_URL'),
#             username=os.getenv('NEO4J_USERNAME'),
#             password=os.getenv('NEO4J_PASS')
#         )
#         knowledge_base = KnowledgeBase(n4j_graph, bootstrap_knowledge_dir)
#         loaded_pdfs = knowledge_base.load_pdfs()
#         chunked_docs = knowledge_base.split_docs(loaded_docs=loaded_pdfs)
#         knowledge_base.add_docs_to_graph(chunked_docs=chunked_docs)
#         # set it to the app context
#         app.knowledge_base = knowledge_base
#     except Exception as ex:
#         raise ex

class FlaskTask(Task):
    def __call__(self, *args, **kwargs):
        with current_app.app_context():
            return self.run(*args, **kwargs)

def create_celery_app(app=None):
    """
    Create a new Celery app and tie it with the Flask app's Celery Config.
    Wrap all tasks in the context of the application.
    """
    celery_app = Celery(app.import_name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config.get("CELERY_CONFIG", {}))
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    
    return celery_app

def create_rpc_clients(app):
    """ Attach the RPC clients to the application's context """
    try:    
        image_search_rpc = PubSubRPCClient(
            project_id=os.getenv('PROJECT_ID'),
            topic_name=os.getenv('IMAGE_SEARCH_TOPIC'),
            subscription_name=os.getenv('IMAGE_SEARCH_SUB_ID'),
        )
        app.extensions["image_search_rpc"] = image_search_rpc
        datasynth_rpc = PubSubRPCClient(
            project_id=os.getenv('PROJECT_ID', ''),
            topic_name=os.getenv('DATASYNTH_TOPIC', ''),
            subscription_name=os.getenv('DATASYNTH_SUB_ID', ''),
        )
        app.extensions["datasynth_rpc"] = datasynth_rpc
    except Exception as ex:
        logging.error(f"Error occured while creating RPC clients : {ex}")

def create_app():
    """ Create a Flask application using the app factory pattern. """
    app = Flask(__name__)
    app.secret_key = 'ECOLENS_SECRET_123'
    app.config.from_mapping(
        CELERY=dict(
            broker_url=os.getenv("CELERY_BROKER_URL"),
            result_backend=os.getenv("CELERY_RESULT_BACKEND"),
            task_ignore_result=True,
        ),
    )
    app.config.from_prefixed_env()
    create_celery_app(app)
    # environment_config = os.getenv('CONFIG_SETUP', '')
    # app.config.from_object(environment_config)

    create_rpc_clients(app)
    # create_knowledge_base(app, os.getenv("BOOTSTRAP_KNOWLEDGE_DIR", None))

    middleware(app)
    app.register_blueprint(gen_search_bp, url_prefix="/api")

    with app.app_context():
        app.db_session = db_session
    
    return app
    

def middleware(app) -> None:
    app.wsgi_app = ProxyFix(app.wsgi_app)
    return None

app = create_app()

@app.route('/health')
def health():
    return 'Its is alive!\n'