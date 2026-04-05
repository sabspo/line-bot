from flask import Flask, request
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def hello():
    return "Hello LINE Bot!"

@app.route("/callback", methods=["POST"])
def callback():
    print("Webhook来た！！！")
    data = request.json
    print(data)
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)