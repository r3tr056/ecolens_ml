
import logging
from celery import shared_task
from lamini import LaminiClassifier
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from apps.core.models.product import Category
from apps.ecodome.data_synthesis.data_models import EPDData, LCAData, ProductEnvironmentTags


@shared_task
def create_category_classifier(db_session):
    categories = db_session.query(Category).all()
    categories_data = {category.id: [category.name, category.desc] for category in categories}
    llm = LaminiClassifier()
    llm.prompt_train(categories_data)
    llm.save("models/category_classifier.lamini")
    return llm

@shared_task
def create_or_get_category(product_name, product_desc, db_session, classifier):
    category_id = classifier.predict({f"{product_name} : {product_desc}"})[0]
    category = db_session.query(Category).filter_by(id=category_id).first()
    if category:
        return category
    else:
        # create a new category
        pass

@shared_task(ignore_result=False)
def generate_env_tags(llm, epd_data):
    try:
        parser = PydanticOutputParser(pydantic_object=ProductEnvironmentTags)
        GENERATE_PROMPT = f"Based on this EPD Data :\n{epd_data}\n Generate Environment Tags for the product. (generate AT LEAST 5 tags)"
        prompt = PromptTemplate(
            template=GENERATE_PROMPT,
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        chain = prompt | llm | parser
        return chain.invoke()
    except Exception as ex:
        logging.error(f"Error occured while generating lca data : {ex}")

@shared_task(ignore_result=False)
def get_lca_data(llm, product_name, product_description=None, google_search_result=None):
    try:
        parser = PydanticOutputParser(pydantic_object=LCAData)
        GENERATE_PROMPT = f"On the basis of the given information:\n Product Name: {product_name}, Product Description : {product_description}\n Results from Google Search : {google_search_result}. Break down the production of the product into discrete Manufacturing steps."
        prompt = PromptTemplate(
            template=GENERATE_PROMPT,
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        chain = prompt | llm | parser
        return chain.invoke()
    except Exception as ex:
        logging.error(f"Error occured while generating lca data : {ex}")

@shared_task(ignore_result=False)
def get_epd_data(llm, product_name, product_description, epd_docs=None, lca_data=None):
    try:
        if not lca_data:
            lca_names = [metric.name for metric in lca_data]
            lca_values = [metric.value for metric in lca_data]
            lca_units = [metric.unit for metric in lca_data]
            lca_data = [
                f"Name: {name}, Value: {value}, Unit: {unit}" for name, value, unit in zip(lca_names, lca_values, lca_units)
            ]
            lca_data = "\n".join(lca_data)

        parser = PydanticOutputParser(pydantic_object=EPDData)
        prompt = PromptTemplate(
            template="Based on the information:\nProduct Name:{product_name}, Product Description:{product_description}\nEPD Information:\n{epd_docs}\nLCA Data\n{lca_data}\nSummarize the information as a long Environmental Decleration",
            input_variables=["product_name", "product_description", "epd_docs", "lca_data"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        chain = prompt | llm | parser
        return chain.invoke({"product_name": product_name, "product_description": product_description, "epd_docs": epd_docs, "lca_data": lca_data})
    except Exception as ex:
        logging.error(f"Error occured while generating epd report data : {ex}")
