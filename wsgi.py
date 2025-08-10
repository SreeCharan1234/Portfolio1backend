import os
from app import app

if __name__ == "__main__":
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get("PORT", 10000))
    # Run the app with the port explicitly set
    app.run(host="0.0.0.0", port=port)
