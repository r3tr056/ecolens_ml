
from typing import List
from google.cloud import vision_v1p4beta1 as vision

client = vision.ImageAnnotatorClient()

async def detect_labels_product_image(image_gcs_url: str) -> List[str]:
    """ Detects image features in a JPGE/PNG file """
    image = vision.Image()
    image.source.image_uri = image_gcs_url
    response = client.label_detection(image=image)
    labels = [label.description.lower() for label in response.label_annotations]
    return labels

async def detect_barcode(barcode_image: bytes) -> List[str]:
    """ Detects and converts a barcode into data """
    image = vision.Image(barcode_image)
    response = await client.text_detection(image=image)
    barcodes = [barcode.data for barcode in response.barcode_annotations]
    return barcodes
