import os
import logging
from apps.app import app
from apps.rpc_methods.utils import process_image_reference
from apps.cloudvision.image_annotation import detect_labels_product_image, detect_barcode
from apps.tasks.google_search import async_google_image_search

image_search_rpc = app.extensions['image_search_rpc']

@image_search_rpc.remote_method('detect-image')
async def detect_image(image_reference):
    image_file = process_image_reference(image_reference)
    if image_file is None:
        return {"error": "No image provided"}
    product_image = image_file.read()

    # Extract labels from the product image
    labels = detect_labels_product_image(product_image)
    # TODO : Better if we move this to the react app
    barcode_data = detect_barcode(product_image)
    result = {"labels": labels, "barcode": barcode_data}
    logging.debug(result)
    return result

@image_search_rpc.remote_method('similar-images')
async def find_similar_images(image_url):
    _, _, image_links = async_google_image_search(image_url)
    return {"image_links": image_url}