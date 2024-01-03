from flask import jsonify
import pandas as pd
import pymysql.cursors
from decouple import config

def getDataSOP():
    # Update the database connection information
    database_config = {
        'host': config('DB_HOST', 'localhost'),
        'user': config('DB_USERNAME', 'root'),
        'password': config('DB_PASSWORD', ""), 
        'db': config('DB_DATABASE', "nurtura_grow"),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

    connection = pymysql.connect(**database_config)

    try:
        with connection.cursor() as cursor:
            # Select all data from SOP_Pengairan table
            sql = "SELECT * FROM sop_pengairan"
            cursor.execute(sql)

            # Fetch all the rows
            rows = cursor.fetchall()

            # Organize the data
            data = {
                'temperature_min': None,
                'temperature_max': None,
                'humidity_min': None,
                'humidity_max': None,
                'soil_moisture_min': None,
                'soil_moisture_max': None,
            }
            
            for row in rows:
                if row['nama'] == 'temperature':
                    data['temperature_min'] = int(row['min'])
                    data['temperature_max'] = int(row['max'])
                elif row['nama'] == 'humidity':
                    data['humidity_min'] = int(row['min'])
                    data['humidity_max'] = int(row['max'])
                elif row['nama'] == 'soil_moisture':
                    data['soil_moisture_min'] = int(row['min'])
                    data['soil_moisture_max'] = int(row['max'])
                    
            return data;

    finally:
        # Close the connection
        connection.close()

# Define the function to classify based on the criteria
def label_cluster(soil_moisture, humidity, temperature):
    data = getDataSOP();
    
    hasil_tanah = 0
    hasil_udara = 0

    if data['temperature_min'] <= temperature < data['temperature_max']:
        hasil_tanah = 3
        hasil_udara = 3

        if soil_moisture > data['soil_moisture_max']:
            hasil_tanah = 1
            hasil_udara = 1

        elif data['soil_moisture_min'] <= soil_moisture <= data['soil_moisture_max']:
            hasil_tanah = 2
            hasil_udara = 3

            if humidity > data['humidity_max']:
                hasil_udara = 1

            elif data['humidity_min'] <= humidity <= data['humidity_max']:
                hasil_udara = 2

    elif temperature < data['temperature_min'] or temperature >= data['temperature_max']:
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
