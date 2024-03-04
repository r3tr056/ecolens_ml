import os
import logging
from typing import Dict, List
from apps.app import app
from apps.core.pubsub.client import PubSubRPCClient
from apps.ecodome.data_synthesis.data_synthesis import data_syntheisis

datasynth_rpc = app.extensions['datasynth_rpc']

@datasynth_rpc.remote_method('process-image')
def start_data_synth(search_term: str, labels: List[str], product_image_url: str, barcode_data: str) -> Dict:
    product_id = data_syntheisis(
        search_term=search_term,
        barcode_data=barcode_data,
        product_image_url=product_image_url,
        labels=labels
    )
    
    return {'product_id': product_id}
