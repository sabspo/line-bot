from flask import Flask, request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def hello():
    return "Hello LINE Bot!"

@app.route("/callback", methods=["GET", "POST"])
def callback():
    if request.method == "GET":
        return "callback ok"

    print("Webhook来た！！！")
    data = request.json
    print(data)
    return "OK"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)