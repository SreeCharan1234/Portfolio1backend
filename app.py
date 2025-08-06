from flask import Flask, request
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)

@app.route('/', methods=['GET', 'POST'])
def hello():
    """
    This endpoint returns a welcome message.
    ---
    responses:
      200:
        description: A friendly greeting
        examples:
          text: Hi, this is Sree Charan
    """
    data = request.data or request.args or request.form
    print("Incoming data:", data)
    return "Hi, this is Sree Charan"

if __name__ == '__main__':
    app.run()
