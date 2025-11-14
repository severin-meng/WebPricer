from flask import Flask, request, jsonify
from pricer_wrapper import CppPricer

app = Flask(__name__)
pricer = CppPricer("./pricer_service")

@app.route("/price", methods=["POST"])
def price():
    data = request.json              # JSON request from client
    result = pricer.query(data)      # forward to C++ pricer
    return jsonify(result)           # send JSON response

@app.route("/shutdown", methods=["POST"])
def shutdown():
    pricer.stop()
    return jsonify({"status": "pricer stopped"})

if __name__ == "__main__":
    app.run(debug=True)
