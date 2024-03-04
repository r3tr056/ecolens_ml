
import requests

class EPDClient:
    def __init__(self):
        self.api_url = "https://epd-apim.environdec.com/stg/api/v1/EPDs"

    def search_epds(self, search_string="", updated_from="", updated_to="", skip=0, take=50):
        params = {
            "SearchString": search_string,
            "UpdatedFrom": updated_from,
            "UpdatedTo": updated_to,
            "Skip": skip,
            "Take": take
        }

        response = requests.get(self.api_url, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error : {response.status_code}")
            return None
        
    def get_epd_file_content(self, registration_number, file_id):
        api_url = f"{self.api_url}/{registration_number}/files/{file_id}"
        response = requests.get(api_url)

        if response.status_code == 200:
            return response.content
        else:
            print(f"Error : {response.status_code}")
            return None
