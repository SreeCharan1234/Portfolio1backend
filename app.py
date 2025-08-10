from flask import Flask, request, jsonify
from flasgger import Swagger, swag_from
from test import load_data, preprocess_data, find_similar_content
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

app = Flask(__name__)

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}

swagger = Swagger(app, config=swagger_config)

GEMINI_API_KEY = "AIzaSyAWDUMXlv5JWhQOqDuBHBu01WijtD0igBE"  # Replace with your actual key
genai.configure(api_key=GEMINI_API_KEY)

# Load and preprocess data once at startup
json_file_path = "sreedata.json"
data = load_data(json_file_path)
text_chunks, original_data = preprocess_data(data)
model = SentenceTransformer('all-MiniLM-L6-v2')

@app.route("/chat", methods=["POST"])
@swag_from({
    "tags": ["Chat API"],
    "summary": "Get response from Gemini based on portfolio data",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "schema": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User query about the portfolio"
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Successful response",
            "schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "context_used": {"type": "array"},
                    "gemini_response": {"type": "string"}
                }
            }
        },
        "400": {
            "description": "Bad request",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            }
        },
        "500": {
            "description": "Server error",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            }
        }
    }
})
def chat():
    try:
        user_query = request.json.get("query", "")

        if not user_query:
            return jsonify({"error": "Query is required"}), 400

        # Find similar content
        similar_content = find_similar_content(user_query, text_chunks, original_data, model)

        # Prepare context for Gemini
        context_text = "\n".join(
            [str(item["content"]) for item in similar_content]
        )
        prompt = f"Context:\n{context_text}\n\nUser Query: {user_query}\nAnswer based on the context above."

        # Call Gemini with a valid model name
        # Using gemini-1.5-flash which is a valid model name
        response = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)

        return jsonify({
            "query": user_query,
            "context_used": similar_content,
            "gemini_response": response.text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
@swag_from({
    "tags": ["Home"],
    "summary": "API home endpoint",
    "responses": {
        "200": {
            "description": "Welcome message",
            "schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "status": {"type": "string"}
                }
            }
        }
    }
})
def home():
    return jsonify({
        "message": "Portfolio AI Chat API is running",
        "status": "online"
    })

if __name__ == "__main__":
    # Run the app on 0.0.0.0 to make it accessible from any network interface
    # Default port is 5000, but explicitly stating it for clarity
    app.run(host='0.0.0.0', port=5000, debug=True)
