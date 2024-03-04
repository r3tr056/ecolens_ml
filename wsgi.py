
import os
from dotenv import load_dotenv

load_dotenv()

from apps.app import app

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)