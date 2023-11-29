from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from penyiraman import klasifikasi_pengairan
from pemupukan import rekomendasi_pupuk_api

application = Flask(__name__)
cors = CORS(application)
application.config['CORS_HEADERS'] = 'Content-Type'

@application.route('/', methods=['GET'])
@cross_origin()
def index():
    return jsonify({"message": "Hello, World!"});

@application.route("/pemupukan", methods=["POST"])
@cross_origin()
def pemupukan_api():
    try:
        input_data = request.get_json()
        if not input_data:
            raise ValueError("No input data provided")

        tinggi_tanaman = input_data.get("tinggi_tanaman")
        hst = input_data.get("hst")

        if hst is None:
            raise ValueError("HST is required")

        result = rekomendasi_pupuk_api(tinggi_tanaman, hst)
        return result

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@application.route("/penyiraman", methods=["POST"])
@cross_origin()
def penyiraman_api():
    try:
        input_data = request.get_json()
        if not input_data:
            raise ValueError("No input data provided")
        
        if input_data.get("SoilMoisture") is None:
            raise ValueError("SoilMoisture is required")
        if input_data.get("Humidity") is None:
            raise ValueError("Humidity is required")
        if input_data.get("temperature") is None:
            raise ValueError("temperature is required")

        result = klasifikasi_pengairan(input_data)
        return result

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    application.run()
