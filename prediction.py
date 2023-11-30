# prediction_module.py
import pandas as pd
import json
import statsmodels.api as sm
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from decouple import config

username = config("DB_USERNAME", "root")
password = config("DB_PASSWORD", "")
host = config("DB_HOST", "127.0.0.1")
port = config("DB_PORT", "3306")
database = config("DB_DATABASE", "nurtura_grow")

def prediction():
    # Ganti nilai variabel berikut dengan informasi koneksi database PHPMyAdmin Anda
    database_url = f"mysql://{username}:{password}@{host}:{port}/{database}"
    engine = create_engine(database_url)

    # Ganti nilai variabel berikut dengan nama tabel yang sesuai
    table_name = "data_sensor"

    # Ganti kolom-kolom sesuai kebutuhan
    columns_to_select = [
        "timestamp_pengukuran",
        "kelembapan_tanah",
        "kelembapan_udara",
        "suhu",
    ]

    # Buat query SQL untuk memilih kolom-kolom yang diinginkan
    query = f"SELECT {', '.join(columns_to_select)} FROM {table_name} ORDER BY timestamp_pengukuran ASC"

    # Baca data dari tabel ke dalam DataFrame
    df = pd.read_sql_query(query, con=engine)

    df = df.rename(
        columns={
            "timestamp_pengukuran": "Time",
            "kelembapan_tanah": "SoilMoisture",
            "kelembapan_udara": "Humidity",
            "suhu": "temperature",
        }
    )

    # Menggunakan interpolasi linier untuk mengisi nilai-nilai hilang
    df["SoilMoisture"] = df["SoilMoisture"].interpolate(method="linear")
    df["Humidity"] = df["Humidity"].interpolate(method="linear")
    df["temperature"] = df["temperature"].interpolate(method="linear")

    # Set kolom 'Time' sebagai indeks
    df.set_index("Time", inplace=True)

    # Pisahkan dataset menjadi 3 dataset
    df_soil_moisture = df[["SoilMoisture"]]
    df_humidity = df[["Humidity"]]
    df_temperature = df[["temperature"]]

    # Pembagian data menjadi training dan testing set
    def train_test_split(data, test_size=0.2):
        split_idx = int(len(data) * (1 - test_size))
        train_set, test_set = data[:split_idx], data[split_idx:]
        return train_set, test_set

    # Membuat training dan testing set untuk masing-masing variabel
    train_soil_moisture, test_soil_moisture = train_test_split(
        df_soil_moisture, test_size=0.2
    )
    train_humidity, test_humidity = train_test_split(df_humidity, test_size=0.2)
    train_temperature, test_temperature = train_test_split(
        df_temperature, test_size=0.2
    )

    # Fungsi untuk melakukan prediksi menggunakan ARIMA
    def arima_predict(data, hours, order):
        # Membuat model ARIMA
        model = sm.tsa.ARIMA(data, order=order)

        # Melatih model ARIMA
        model_fit = model.fit()

        # Melakukan prediksi untuk waktu ke depan
        forecast = model_fit.forecast(steps=hours)

        return forecast

    # Lakukan prediksi 1 jam ke depan untuk SoilMoisture
    order_soil_moisture = (2, 1, 1)
    predicted_soil_moisture_1_hour_arima = arima_predict(
        df_soil_moisture, 1, order_soil_moisture
    )

    # Lakukan prediksi 1 jam ke depan untuk Humidity
    order_humidity = (1, 0, 1)
    predicted_humidity_1_hour_arima = arima_predict(df_humidity, 1, order_humidity)

    # Lakukan prediksi 1 jam ke depan untuk Temperature
    order_temperature = (0, 0, 0)
    predicted_temperature_1_hour_arima = arima_predict(
        df_temperature, 1, order_temperature
    )

    # Buat DataFrame hasil prediksi
    predicted_data = pd.DataFrame(
        {
            "Time": [df.index[-1] + timedelta(hours=1)],
            "SoilMoisture": predicted_soil_moisture_1_hour_arima,
            "Humidity": predicted_humidity_1_hour_arima,
            "Temperature": predicted_temperature_1_hour_arima,
        }
    )

    # Convert DataFrame to JSON
    predicted_json = predicted_data.to_json(
        orient="records", date_format="iso", default_handler=str
    )

    # Format time in the JSON
    json_dict = json.loads(predicted_json)
    json_dict[0]["Time"] = pd.to_datetime(json_dict[0]["Time"]).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Convert back to JSON with the desired time format
    formatted_json = json.dumps(json_dict[0], default=str)

    return formatted_json
