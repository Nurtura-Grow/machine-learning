from flask import jsonify
import pandas as pd


# Define the function to classify based on the criteria
def label_cluster(soil_moisture, humidity, temperature):
    hasil_tanah = 0
    hasil_udara = 0

    if 25 <= temperature < 33:
        hasil_tanah = 3
        hasil_udara = 3

        if soil_moisture > 69:
            hasil_tanah = 1
            hasil_udara = 1

        elif 50 <= soil_moisture < 69:
            hasil_tanah = 2
            hasil_udara = 3

            if humidity > 69:
                hasil_udara = 1

            elif 60 <= humidity < 69:
                hasil_udara = 2

    elif temperature > 33:
        hasil_tanah = 1.5
        hasil_udara = 1.5

    elif temperature < 25:
        hasil_tanah = 1.2
        hasil_udara = 1.2

    return pd.Series([hasil_tanah, hasil_udara])


# Define the function to evaluate the condition
def evaluate_condition(hasil_tanah, hasil_udara):
    conditions = {
        (1, 1): ("Tanah sudah optimal", "Tidak diperlukan penyiraman"),
        (2, 1): (
            "Tanah cukup lembab, kelembaban udara tinggi",
            "Tidak diperlukan penyiraman",
        ),
        (2, 2): (
            "Tanah cukup lembab, kelembaban udara sedang",
            "Diperlukan sedikit penyiraman",
        ),
        (2, 3): (
            "Tanah cukup lembab, kelembaban udara rendah",
            "Diperlukan sedikit penyiraman untuk menaikkan kelembaban udara",
        ),
        (3, 3): ("Tanah kering", "Diperlukan penyiraman dengan volume yang besar"),
        (1.5, 1.5): ("Suhu udara tinggi", "Tidak diperlukan penyiraman"),
        (1.2, 1.2): ("Suhu udara rendah", "Tidak diperlukan penyiraman"),
    }

    return conditions.get(
        (hasil_tanah, hasil_udara),
        ("Kondisi tidak diketahui", "Saran tidak diketahui"),
    )


# Define the function to determine "nyala" and "waktu" based on cluster
def set_nyala_waktu(cluster):
    if 1 <= cluster < 1.5:
        return {"nyala": False, "waktu": 0}
    elif 1.5 <= cluster <= 2.5:
        return {"nyala": True, "waktu": 600}
    elif cluster == 3:
        return {"nyala": True, "waktu": 3000}
    else:
        return {}  # When the cluster does not match any condition

def klasifikasi_pengairan(input_data):
    try:
        new_data = pd.DataFrame([input_data])
        new_data[["Hasil_Tanah", "Hasil_Udara"]] = new_data.apply(
            lambda row: label_cluster(
                row["SoilMoisture"], row["Humidity"], row["temperature"]
            ),
            axis=1,
        )
        kondisi, saran = evaluate_condition(
            new_data["Hasil_Tanah"].iloc[0],
            new_data["Hasil_Udara"].iloc[0],
        )
        new_data["Cluster"] = (
            new_data["Hasil_Tanah"] + new_data["Hasil_Udara"]
        ) / 2
        info = set_nyala_waktu(new_data["Cluster"].iloc[0])

        # Return the response
        response = {"Kondisi": kondisi, "Saran": saran, "Informasi Kluster": info}
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
