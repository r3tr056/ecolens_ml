
![Ecoview Google Cloud Architecture](/.github/assets/cloud_arch.jpg "Optional title")


**Core Structure**

The architecture seems built around a microservices model, with traffic entering from two primary sources:

* **Web Browser:** Traditional web application access.
* **Mobile Client:** Users interacting through a mobile app.

**Front-End**

* **Cloud Load Balancing:** Distributes incoming traffic across multiple backend instances for scalability and resilience. This is a critical component for handling varying user loads.
* **Cloud DNS:** Translates domain names (like ecolens.view) into IP addresses, allowing users to connect seamlessly.

**Application Tier**

* **ecolens_react:** Likely a React-based frontend application hosted on App Engine. App Engine provides a flexible, managed environment for web app deployment.
* **ecolens_api:** This is probably a RESTful API serving data and functionality. It might be implemented on Cloud Run (for container-based microservices) or App Engine.
* **Cloud Endpoints:** A service to manage, secure, and monitor APIs, ensuring controlled access to the backend.

**Data Tier**

* **Cloud SQL (pg_ecolens):** A managed PostgreSQL database for structured data storage.
* **Cloud Storage (ecolens data):** Highly scalable storage for images, videos, and other unstructured data.
* **Pub/Sub:** A messaging service enabling asynchronous communication between microservices, making the system more loosely coupled.

**Machine Learning / AI**

* **ecolens_ml:**  This suggests a machine learning component possibly deployed on Cloud Run.
* **Vision API:** Pre-trained Google image analysis service for tasks like object detection, classification, etc.
* **Natural Language API:** Pre-trained Google language processing tool for sentiment analysis, entity recognition, and more.
* **Image Annotation API:**  Presumably used to automatically label images within the system, aiding in search and management.

**Development & Operations**

* **Github:** Code repository for version control.
* **Github Actions:**  For CI/CD (continuous integration/continuous delivery) pipelines to automate builds, testing, and deployment.
* **Application Logs:**  Centralized logging for monitoring and troubleshooting.

