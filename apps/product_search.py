from google.cloud import vision
from google.protobuf import field_mask_pb2 as field_mask

def get_product(project_id, location, product_id):
    client = vision.ProductSearchClient()

    # Get the full path of the product
    product_path = client.product_path(
        project=project_id, location=location, product=product_id
    )

    product = client.get_product(name=product_path)

    