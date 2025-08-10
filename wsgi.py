import os
from app import app

# For Render deployment
port = int(os.environ.get("PORT", 10000))
print(f"Running on port: {port}")

if __name__ == "__main__":
    # Run the app with the port explicitly set
    app.run(host="0.0.0.0", port=port)
