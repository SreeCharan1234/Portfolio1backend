# Portfolio Backend API

This is a Flask API backend for a portfolio website that uses Google's Generative AI to answer questions about the portfolio data.

## Setup

1. Clone the repository
2. Create a virtual environment and activate it
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Unix or MacOS
   source venv/bin/activate
   ```
3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment variables in a `.env` file (see .env.example)
5. Run the application
   ```bash
   python app.py
   ```

## API Documentation

Once the application is running, you can access the Swagger documentation at:

```
http://localhost:5000/docs
```

## Endpoints

- `GET /`: Home endpoint to check if the API is running
- `POST /chat`: Send a query to get information about the portfolio

## Deployment to Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Use the following settings:
   - Environment: Python
   - Build Command: `./build.sh`
   - Start Command: `gunicorn wsgi:app`
4. Add environment variables:
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `PORT`: 10000 (Render's default)
   - `FLASK_DEBUG`: 0

### Troubleshooting Render Deployment

If you encounter "Out of memory" errors on Render:
- Make sure to use the `render.yaml` configuration file
- Ensure your environment is correctly set up with all environment variables
- The app is configured to lazy-load the ML model to save memory
- If still encountering issues, consider upgrading your Render plan for more resources

## Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key
- `PORT`: Port to run the application (default: 5000)
- `HOST`: Host to run the application (default: 0.0.0.0)
- `FLASK_DEBUG`: Enable debug mode (0 or 1, default: 0)

## Technologies Used

- Flask
- Google Generative AI
- Sentence Transformers
- Flasgger (Swagger)
