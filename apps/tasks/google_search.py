import os
import logging
from serpapi import GoogleSearch
from langchain_community.utilities.google_search import GoogleSearchAPIWrapper

from apps.core.cache.redis_cache import redis_cache

@redis_cache(ttl=3600)
def async_google_image_search(image_url):
    try:
        params = {
            'api_key': os.environ.get('SERP_API_KEY'),
            'engine': 'google_lens',
            'url': image_url,
            'hl': 'en',
        }
        search = GoogleSearch(params)
        response = search.json()
        if response["search_metadata"]["status"] != "Success":
            logging.error(f"Google Lens search for {image_url} failed")

        subject = None
        subject_link = None
        image_links = []

        if len(response.get("knowledge_graph")) > 0:
            subject = response["knowledge_graph"][0]
            subject = f"{subject.get('title')}({subject.get('subtitle')})"
            subject_link = subject['link']

        for image in response.get("visual_matches", []):
            if image['source'].endswith('.jpg') or image['source'].endswith('.png'):
                image_links.append(image['source'])
            else:
                image_links.append(image['thumbnail'])

        result = subject, subject_link, image_links
        return result
    except Exception as ex:
        logging.error(f"Error in async_google_image_search: {ex}")
        return None
    
@redis_cache(ttl=3600)
def async_product_google_search(query, num_results=5):
    try:
        search = GoogleSearchAPIWrapper(k=num_results)
        return search.run(query=query)
    except Exception as ex:
        logging.error(f"Error in async_product_google_search : {ex}")
        return None