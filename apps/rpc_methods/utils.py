import hashlib
import io
from urllib.parse import urlparse
from google.cloud import storage

def process_image_reference(message):
    image_reference = message.data.decode('utf-8')
    bucket_name, object_path = image_reference.replace('gs://', '').split('/', 1)
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_path)

    image_stream = io.BytesIO()
    blob.download_to_file(image_stream)
    return image_stream



def url_to_filename(url):
    # Parse the URL to extract the path
    url_path = urlparse(url).path

    # Generate an MD5 hash from the URL
    url_hash = hashlib.md5(url.encode()).hexdigest()

    # Combine the hash with the last part of the URL path to create a unique filename
    filename = f"{url_hash}_{url_path.split('/')[-1]}"

    return filename