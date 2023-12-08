# prediction_module.py
import pandas as pd
import json
import statsmodels.api as sm
from datetime import datetime, timedelta
from pmdarima import auto_arima
import pymysql
from pymysql.cursors import DictCursor
from decouple import config

username = config("DB_USERNAME", "root")
password = config("DB_PASSWORD", "")
host = config("DB_HOST", "127.0.0.1")
port = config("DB_PORT", "3306")
database = config("DB_DATABASE", "nurtura_grow")

# Fungsi untuk mendapatkan data terbaru dari database
def get_latest_data():
    connection = pymysql.connect(
        host=host,
        user=username,
        password=password,
        database=database,
        cursorclass=DictCursor,
    )

    query = "SELECT timestamp_pengukuran, kelembapan_tanah, kelembapan_udara, suhu FROM data_sensor ORDER BY timestamp_pengukuran DESC LIMIT 1"

    with connection.cursor() as cursor:
        cursor.execute(query)
        latest_data = cursor.fetchone()

    connection.close()
    
    return latest_data

# Fungsi untuk membaca data terbaru dari database
def read_latest_data_from_database():
    connection = pymysql.connect(
        host=host,
        user=username,
        password=password,
        database=database,
        cursorclass=DictCursor,
    )

   
    query = "SELECT timestamp_pengukuran, kelembapan_tanah, kelembapan_udara, suhu FROM data_sensor ORDER BY timestamp_pengukuran ASC"

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)

    connection.close()

    df = df.rename(
        columns={
            "timestamp_pengukuran": "Time",
            "kelembapan_tanah": "SoilMoisture",
            "kelembapan_udara": "Humidity",
            "suhu": "temperature",
        }
    )
    
    # Konversi kolom 'Time' ke dalam format datetime
    df['Time'] = pd.to_datetime(df['Time'])
    
    # Hapus duplikat berdasarkan waktu
    df = df.drop_duplicates(subset='Time')
    
    # Set kolom 'Time' sebagai indeks
    df.set_index("Time", inplace=True)
    
    # Resample dengan frekuensi jam ('H') dan isi nilai yang hilang dengan NaN
    df = df.resample('1H').mean()

    # Mengurutkan data berdasarkan waktu
    df = df.sort_values(by='Time')

    # Menggunakan interpolasi linier untuk mengisi nilai-nilai hilang
    df["SoilMoisture"] = df["SoilMoisture"].interpolate(method="linear")
    df["Humidity"] = df["Humidity"].interpolate(method="linear")
    df["temperature"] = df["temperature"].interpolate(method="linear")

    # Pisahkan dataset menjadi 3 dataset
    df_soil_moisture = df["SoilMoisture"]
    df_humidity = df["Humidity"]
    df_temperature = df["temperature"]
    
    # Lakukan differencing pada data
    df_soil_moisture = df_soil_moisture.diff().dropna()
    df_humidity = df_humidity.diff().dropna()
    df_temperature = df_temperature.diff().dropna()

    return df_soil_moisture, df_humidity, df_temperature

# Fungsi untuk training dan prediksi
def train_and_predict(df_soil_moisture, df_humidity, df_temperature, latest_data):
    # Tambahkan data terbaru ke dataset historis
    latest_timestamp = pd.to_datetime(latest_data['timestamp_pengukuran'])
    latest_soil_moisture = latest_data['kelembapan_tanah']
    latest_humidity = latest_data['kelembapan_udara']
    latest_temperature = latest_data['suhu']

    df_soil_moisture.loc[latest_timestamp] = latest_soil_moisture
    df_humidity.loc[latest_timestamp] = latest_humidity
    df_temperature.loc[latest_timestamp] = latest_temperature

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
    auto_order_soil_moisture = auto_arima(df_soil_moisture, seasonal=True, suppress_warnings=True)
    predicted_soil_moisture_1_hour_arima = arima_predict(df_soil_moisture, 1, auto_order_soil_moisture.order)

    # Lakukan prediksi 1 jam ke depan untuk Humidity
    auto_order_humidity = auto_arima(df_humidity, seasonal=True, suppress_warnings=True)
    predicted_humidity_1_hour_arima = arima_predict(df_humidity, 1, auto_order_humidity.order)

    # Lakukan prediksi 1 jam ke depan untuk Temperature
    auto_order_temperature = auto_arima(df_temperature, seasonal=True, suppress_warnings=True)
    predicted_temperature_1_hour_arima = arima_predict(df_temperature, 1, auto_order_temperature.order)

    # Kembalikkan proses differencing untuk mendapatkan prediksi dalam skala asli
    last_soil_moisture_value = df_soil_moisture.iloc[-1]
    predicted_soil_moisture_1_hour_arima = last_soil_moisture_value + predicted_soil_moisture_1_hour_arima.cumsum()

    last_humidity_value = df_humidity.iloc[-1]
    predicted_humidity_1_hour_arima = last_humidity_value + predicted_humidity_1_hour_arima.cumsum()

    last_temperature_value = df_temperature.iloc[-1]
    predicted_temperature_1_hour_arima = last_temperature_value + predicted_temperature_1_hour_arima.cumsum()

    # Buat DataFrame hasil prediksi
    predicted_data = pd.DataFrame(
        {
            "Time": [latest_timestamp + timedelta(hours=1)],
            "SoilMoisture": predicted_soil_moisture_1_hour_arima,
            "Humidity": predicted_humidity_1_hour_arima,
            "temperature": predicted_temperature_1_hour_arima,
        }
    )

    return predicted_data

# Fungsi utama untuk mendapatkan prediksi
def get_prediction():
    try:
        # Dapatkan data terbaru dari database
        latest_data = get_latest_data()

        # Baca dataset historis
        df_soil_moisture, df_humidity, df_temperature = read_latest_data_from_database()

        # Lakukan training dan prediksi
        result = train_and_predict(df_soil_moisture, df_humidity, df_temperature, latest_data)

        # Convert DataFrame to JSON
        predicted_json = result.to_json(
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

    except Exception as e:
        return json.dumps({"error": str(e)}, default=str)
