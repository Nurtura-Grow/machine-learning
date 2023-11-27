from flask import jsonify
import pandas as pd

# Define the function to classify based on the criteria
def label_cluster(soil_moisture, humidity, temperature):
    if 25 <= temperature <= 33:
        if soil_moisture > 69:
            volume_hasil_tanah = 1
            volume_hasil_udara = 1
        elif 50 <= soil_moisture <= 69:
            volume_hasil_tanah = 2
            if humidity > 69:
                volume_hasil_udara = 1
            elif 60 <= humidity <= 69:
                volume_hasil_udara = 2
            else:
                volume_hasil_udara = 3
        else:  # SoilMoisture less than 50
            volume_hasil_tanah = 3
            volume_hasil_udara = 3
    elif temperature > 33:
        volume_hasil_tanah = 1.5
        volume_hasil_udara = 1.5
    elif temperature < 25:
        volume_hasil_tanah = 1.2
        volume_hasil_udara = 1.2
    else:
        volume_hasil_tanah = 0
        volume_hasil_udara = 0

    return pd.Series([volume_hasil_tanah, volume_hasil_udara])

# Define the function to evaluate the condition
def evaluate_condition(volume_hasil_tanah, volume_hasil_udara):
    conditions = {
        (1, 1): ("Tanah sudah optimal", "Tidak diperlukan penyiraman"),
        (2, 1): ("Tanah cukup lembab, kelembaban udara tinggi", "Tidak diperlukan penyiraman"),
        (2, 2): ("Tanah cukup lembab, kelembaban udara sedang", "Diperlukan sedikit penyiraman"),
        (2, 3): ("Tanah cukup lembab, kelembaban udara rendah", "Diperlukan sedikit penyiraman untuk menaikkan kelembaban udara"),
        (3, 3): ("Tanah kering", "Diperlukan penyiraman dengan volume yang besar"),
        (1.5, 1.5): ("Suhu udara tinggi", "Tidak diperlukan penyiraman"),
        (1.2, 1.2): ("Suhu udara rendah", "Tidak diperlukan penyiraman"),
    }

    return conditions.get((volume_hasil_tanah, volume_hasil_udara), ("Kondisi tidak diketahui", "Saran tidak diketahui"))

# Define the function to determine "nyala" and "waktu" based on cluster
def set_nyala_waktu(cluster):
    if 1 <= cluster < 1.5:
        return {"nyala": False}
    elif 1.5 <= cluster <= 2.5:
        return {"nyala": True, "waktu": 600}
    elif cluster == 3:
        return {"nyala": True, "waktu": 3000}
    else:
        return {}  # When the cluster does not match any condition

def klasifikasi_pengairan(input_data):
    try:
        new_data = pd.DataFrame([input_data])
        new_data[['Volume_Hasil_Tanah', 'Volume_Hasil_Udara']] = new_data.apply(
            lambda row: label_cluster(row['SoilMoisture'], row['Humidity'], row['temperature']), axis=1)
        kondisi, saran = evaluate_condition(new_data['Volume_Hasil_Tanah'].iloc[0], new_data['Volume_Hasil_Udara'].iloc[0])
        new_data['Cluster'] = (new_data['Volume_Hasil_Tanah'] + new_data['Volume_Hasil_Udara']) / 2
        info = set_nyala_waktu(new_data['Cluster'].iloc[0])

        # Append the new data to the CSV file
        new_data.to_csv('data_cuaca_dengan_cluster_baru.csv', mode='a', header=False, index=False)

        # Return the response
        response = {
            "Kondisi": kondisi,
            "Saran": saran,
            "Informasi Kluster": info
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500