import os
import logging
from typing import List
from celery import group, chord
from langchain_google_genai import GoogleGenerativeAI
from apps.core.db import db_session
from apps.tasks import get_task_result
from sqlalchemy.exc import SQLAlchemyError
from apps.core.models.epd import EnvironmentalProductDecleration, LCAMetric
from apps.core.models.product import EnvironmentTag, Product
from apps.tasks.google_search import perform_barcode_search, perform_image_search, perform_product_google_search
from apps.tasks.generate_data import create_category_classifier, create_or_get_category, generate_env_tags, get_epd_data, get_lca_data


llm = GoogleGenerativeAI(
    google_api_key=os.getenv('GOOGLE_GEN_AI_API_KEY', ''),
    model="gemini-pro",
)

# def store_in_knowledge_base(knowledge_base, product_instance, env_tags, epd_data, lca_metric_data):
#     """ Store the data in knowledge base """
#     product_graph_data = {
#         "Product": {
#             "name": f"{product_instance.name}",
#             "barcode": product_instance.barcode if product_instance.barcode else '',
#             "images": product_instance.images,
#         },
#         "EnvTags": env_tags,
#         "EPDData": epd_data.description,
#         "LCAData": [f"{lca_metric.name}: {lca_metric.value} {lca_metric.unit}" for lca_metric in lca_metric_data]
#     }
#     knowledge_base.add_dict_to_graphdb(product_graph_data)


def data_syntheisis(search_term, product_image_url: str, labels: List[str], barcode_data: str):
    """
    Performs data synthesis for a product based on various sources

    This function gathers information about a product from multiple sources
    and synthesizes them to create a comprehensive product entry in the database
    It leverages:
    - Google Search for product name and information
    - Image Search for additional information and similar images
    - Google Search with barcode data for more information

    Args:
    - search_term (str): Optional search term to find product information.
    - product_image_url (str): URL of the product image (optional).
    - labels (List[str]): List of product labels extracted from the image (optional).
    - barcode_data (str): Parsed data from the product barcode (optional).

    Returns:
    - int: ID of the created product instance.
    """
    assert search_term or labels, "At least one of search_term or labels should be provided."

    google_search_result, barcode_search_result, product_name, product_link, image_results = None, None, None, None, None

    try:
        if search_term or labels:
            # perform a google search to get the product name
            product_name_search_str = f"What is the official product name/commercial name of {search_term if search_term else labels[0]}"
            product_name = perform_product_google_search(product_name_search_str)
            google_search_result = perform_product_google_search(search_term if search_term else labels[0])

        if product_image_url:
            product_name, product_link, image_results = perform_image_search(product_image_url)

        product_instance = Product.create_from_data(
            product_name=product_name,
            product_desc=google_search_result,
            barcode_data=barcode_data,
            image_results=image_results,
        )
        db_session.add(product_instance)
        db_session.commit()

        create_epd_model_task = create_epd_model.delay(
            product_id=product_instance.id,
            product_name=product_instance.name,
            product_description=product_instance.desc,
        )
        epd_data, epd_id = get_task_result(create_epd_model_task.id)

        create_env_tags_task = create_env_tags.delay(
            product_instance=product_instance,
            epd_data=epd_data,
        )

        get_lca_data_task = get_lca_data.delay(
            product_name=product_instance.name,
            product_description=product_instance.description,
            google_search_result=google_search_result,
            epd_id=epd_id,
        )

        env_tags = get_task_result(create_env_tags_task.id)
        lca_metric_data = get_task_result(get_lca_data_task.id)

        # store_in_knowledge_base(product_instance, env_tags, epd_data, lca_metric_data)

        return product_instance.id
    except Exception as ex:
        logging.error(f"Error while creating data : {ex}")


def create_epd_model(product_id, product_name, product_description):
    """
    Creates an EPD Model for a given product using Ecodome's Data synthesis Engine

    Args:
    - product_id (int): The ID of the product associated with the EPD.
    - product_name (str): The name of the product.
    - product_description (str): The description of the product.
    - llm (object): An object representing the large language model (LLM) to be used.

    Returns:
    tuple: A tuple containing:
        - epd_data (dict): The retrieved EPD data.
        - epd_instance_id (int): The ID of the newly created EPD instance.
    """
    try:
        with db_session() as session:
            epd_data_task = get_epd_data.delay(
                product_name=product_name,
                product_description=product_description,
                llm=llm,
            )
            epd_data = get_task_result(epd_data_task.id)
            epd_instance = EnvironmentalProductDecleration.from_epd_data(
                epd_data,
                product_id
            )
            session.add(epd_instance)
            session.commit()
            return epd_data, epd_instance.id
    except SQLAlchemyError as e:
        db_session.rollback()
        raise e

def create_env_tags(product_instance, epd_data):
    """
    Creates and stores EnvironmentalTags for a product based on the EPD data
    of the product

    Args:
    - product_instance (object): An instance of the product model.
    - epd_data (dict): The EPD data associated with the product.
    - llm (object): An object representing the large language model (LLM) to be used.

    Returns:
    - list: A list of the generated environmental tags.

    Raises:
    - SQLAlchemyError: If any database errors occur during the process.
    """
    try:
        with db_session() as session:
            env_tags_task = generate_env_tags.delay(llm, epd_data)
            env_tags = get_task_result(env_tags_task.id).epd_tags
            for env_tag in env_tags:
                environment_tag = EnvironmentTag(name=env_tag, product=product_instance)
                session.add(environment_tag)
            session.commit()
            return env_tags
    except SQLAlchemyError as ex:
        db_session.rollback()
        raise ex
    
def create_lca_metric_data(product_name, product_description, google_search_result, epd_id):
    """ 
    Retreives and stores Life Cycle Assessment Data for a product.

    Args:
    - product_name (str): The name of the product.
    - product_description (str): The description of the product.
    - google_search_result (object): An object representing the results of a Google search, likely containing relevant information for LCA data extraction.
    - epd_id (int): The ID of the EPD associated with the product.
    - llm (object): An object representing the large language model (LLM) to be used.

    Returns:
    - object: The retrieved LCA metric data object.

    Raises:
    - SQLAlchemyError: If any database errors occur during the process.
    """
    try:
        with db_session() as session:
            lca_metric_data_task = get_lca_data.delay(
                product_name=product_name,
                product_description=product_description,
                llm=llm,
                google_search_result=google_search_result,
            )
            lca_metric_data = get_task_result(lca_metric_data_task.id)

            for lca_metric in lca_metric_data.lca_metrics:
                lca_metric_instance = LCAMetric.from_lca_metric_data(lca_metric, epd_id)
                session.add(lca_metric_instance)
            session.commit()

            return lca_metric_data
    except SQLAlchemyError as e:
        db_session.rollback()
        raise e