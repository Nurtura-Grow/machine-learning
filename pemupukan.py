from flask import jsonify
import pandas as pd

# Load dataset from the CSV file
df = pd.read_csv("dataset.csv")

def calculate_recommendation(tinggi_tanaman, hst):
    # Filter dataset based on the given hst
    data_tanaman = df[df["hst"] == hst]
    
    nyala = False
    waktu = 0
    tinggi_optimal = 0
    message = "Tinggi tanaman atau HST tidak sesuai"
    
    if hst % 3 != 0:
        nyala = False
        tinggi_optimal = 1
        message = "Belum tiba pada jangka waktu yang tepat untuk pelaksanaan pemupukan"

    elif hst % 3 == 0:  
        tinggi_minimal = data_tanaman["tinggi_minimal"].values[0]
        tinggi_maksimal = data_tanaman["tinggi_maksimal"].values[0]

        if tinggi_minimal < tinggi_tanaman < tinggi_maksimal:
            nyala = True
            waktu = 60
            tinggi_optimal = 1
            message = "Tinggi tanaman optimal, jalankan pemupukan sesuai SOP"

        elif tinggi_tanaman > tinggi_maksimal:
            nyala = False
            tinggi_optimal = 0
            message = "Tanaman terlalu tinggi, berikan obat tanaman yang sesuai"

        elif tinggi_tanaman < tinggi_minimal:
            nyala = False
            tinggi_optimal = 0
            message = "Tanaman terlalu pendek, cek pH tanah, jika pH optimal berikan pupuk dengan unsur N tinggi"

    return {
        "nyala": nyala,
        "waktu": waktu,
        "tinggi_optimal": tinggi_optimal,
        "message": message
    }



def rekomendasi_pupuk_api(tinggi_tanaman, hst):
    try:
        result = calculate_recommendation(tinggi_tanaman, hst)
        return jsonify(result)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
