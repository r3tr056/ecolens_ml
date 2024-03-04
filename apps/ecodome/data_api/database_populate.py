import logging
from apps.core.models.epd import EnvironmentalProductDecleration, Report, LCAMetric
from apps.core.models.product import EnvironmentTag, Product, MarketPlaceProduct

session = None

def add_lca_metric_data_to_database(lca_data_list, epd_instance):
    try:
        for lca_data in lca_data_list:
            lca_metric_instance = LCAMetric(
                value=lca_data.value,
                unit=lca_data.unit,
                epd=epd_instance
            )
            session.add(lca_metric_instance)
        session.commit()
        logging.debug("Data successfully saved to the database")
    except Exception as ex:
        session.rollback()
        logging.error(f"Error : {ex}")

def add_epd_data_to_database(product_id, epd_data, lca_data_list):
    try:
        product_instance = Product(id=product_id)
        epd_instance = EnvironmentalProductDecleration(
            product=product_instance,
            description=epd_data.description
        )
        add_lca_metric_data_to_database(lca_data_list, epd_instance)

        session.add(epd_instance)
        session.commit()
        logging.debug("Data successfully saved to the database")
    except Exception as e:
        session.rollback()
        logging.error(f"Error : {e}")

def add_report_to_database(report_data, epd_instance):
    try:
        report_instance = Report(
            epd=epd_instance,
            summary=report_data.summary
        )
        session.add(report_instance)
        session.commit()
        logging.debug("Report data successfully saved to the database")
    except Exception as ex:
        session.rollback()
        logging.error(f"Error : {ex}")