from setuptools import setup, find_packages

setup(
    name="portfolio-backend",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Flask==2.3.3",
        "Flask-CORS==4.0.0",
        "flasgger==0.9.7.1",
        "python-dotenv==1.0.0",
        "Werkzeug==2.3.7",
        "gunicorn==21.2.0",
        "google-generativeai==0.3.2",
        "sentence-transformers==2.2.2",
        "numpy==1.24.0",
        "scikit-learn==1.3.0",
    ],
    python_requires=">=3.10",
)
