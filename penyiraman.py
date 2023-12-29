import pandas as pd
from flask import Flask, jsonify
import pymysql.cursors

app = Flask(__name__)

# Assume the functions label_cluster, evaluate_condition, and set_nyala_waktu are defined here


# Function to fetch sensor parameters from the database
def get_sensor_params():
    # Replace these with your actual database connection details
    host = 'localhost'
    user = 'root'
    password = ''
    database = 'nurtura_grow'

    connection = pymysql.connect(host=host, user=user, password=password, database=database)
    
    try:
        with connection.cursor() as cursor:
            # Assume you have a table named 'sensor_params' with columns 'sensor_id', 'min', and 'max'
            query = "SELECT id, min, max FROM sop_pengairan WHERE id IN (1, 2, 3)"
            cursor.execute(query)
            results = cursor.fetchall()

            params = {
                'temp_min': 0, 'temp_max': 0,
                'hum_min': 0, 'hum_max': 0,
                'soil_min': 0, 'soil_max': 0
            }

            for result in results:
                sensor_id, sensor_min, sensor_max = result
                if sensor_id == 1:
                    params['temp_min'] = sensor_min
                    params['temp_max'] = sensor_max
                elif sensor_id == 2:
                    params['hum_min'] = sensor_min
                    params['hum_max'] = sensor_max
                elif sensor_id == 3:
                    params['soil_min'] = sensor_min
                    params['soil_max'] = sensor_max

            return params
    finally:
        connection.close()

# Define the function to classify based on the criteria
def label_cluster(soil_moisture, humidity, temperature, sensor_params):
    # Fetch sensor parameters from the database
    params = sensor_params

    hasil_tanah = 0
    hasil_udara = 0

    if params['temp_min'] <= temperature < params['temp_max']:
        hasil_tanah = 3
        hasil_udara = 3

        if soil_moisture > params['soil_max']:
            hasil_tanah = 1
            hasil_udara = 1

        elif params['soil_min'] <= soil_moisture <= params['soil_max']:
            hasil_tanah = 2
            hasil_udara = 3

            if humidity > params['hum_max']:
                hasil_udara = 1

            elif params['hum_min'] <= humidity <= params['hum_max']:
                hasil_udara = 2

    elif temperature < params['temp_min'] or temperature >= params['temp_max']:
        hasil_tanah = 1.2
        hasil_udara = 1.2

    return pd.Series([hasil_tanah, hasil_udara])

# Define the function to evaluate the condition
def evaluate_condition(hasil_tanah, hasil_udara):
    conditions = {
        (1.2, 1.2): ("Suhu tidak ideal", "Tidak diperlukan penyiraman"),
        (1, 1): ("Ideal", "Tidak diperlukan penyiraman"),
        (2, 1): (
            "Ideal",
            "Tidak diperlukan penyiraman",
        ),
        (2, 2): (
            "Kurang ideal",
            "Diperlukan sedikit penyiraman",
        ),
        (2, 3): (
            "Kurang Ideal",
            "Diperlukan sedikit penyiraman untuk menaikkan kelembaban udara",
        ),
        (3, 3): ("Kritis", "Diperlukan penyiraman dengan volume yang besar"),
        
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

# Main function for classification and response
def klasifikasi_pengairan(input_data):
    try:
        # Fetch sensor parameters from the database
        sensor_params = get_sensor_params()

        # Create a DataFrame from input_data
        new_data = pd.DataFrame([input_data])

        # Label the cluster based on sensor parameters
        new_data[["Hasil_Tanah", "Hasil_Udara"]] = new_data.apply(
            lambda row: label_cluster(
                row["SoilMoisture"], row["Humidity"], row["temperature"], sensor_params
            ),
            axis=1,
        )

        # Evaluate the condition and get recommendations
        kondisi, saran = evaluate_condition(
            new_data["Hasil_Tanah"].iloc[0],
            new_data["Hasil_Udara"].iloc[0],
        )

        # Calculate the cluster
        new_data["Cluster"] = (
            new_data["Hasil_Tanah"] + new_data["Hasil_Udara"]
        ) / 2

        # Determine "nyala" and "waktu" based on cluster
        info = set_nyala_waktu(new_data["Cluster"].iloc[0])

        # Return the response
        response = {"Kondisi": kondisi, "Saran": saran, "Informasi Kluster": info}
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

