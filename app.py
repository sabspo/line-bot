from flask import Flask, request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def hello():
    return "Hello LINE Bot!"

@app.route("/callback", methods=["POST"])
def callback():
    data = request.json
    print("受信データ:", data)
    return "OK"

if __name__ == "__main__":
    app.run(port=5000)