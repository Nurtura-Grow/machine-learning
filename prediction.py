from tensorflow.keras.models import load_model
import pandas as pd
import pymysql.cursors
from decouple import config

# Update the database connection information
database_config = {
    'host': config('DB_HOST', 'localhost'),
    'user': config('DB_USERNAME', 'root'),
    'password': config('DB_PASSWORD', ""), 
    'db': config('DB_DATABASE', "nurtura_grow"),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_latest_data(model_name):
    connection = pymysql.connect(**database_config)

    try:
        with connection.cursor() as cursor:
            table_name = 'data_sensor'
            columns_to_select = ['timestamp_pengukuran', model_name]
            latest_data_query = f"SELECT {', '.join(columns_to_select)} FROM {table_name} ORDER BY `timestamp_pengukuran` DESC LIMIT 60"
            cursor.execute(latest_data_query)
            result = cursor.fetchall()

    finally:
        connection.close()

    latest_data = pd.DataFrame(result)
    latest_data['timestamp_pengukuran'] = pd.to_datetime(latest_data['timestamp_pengukuran'])
    latest_data.set_index('timestamp_pengukuran', inplace=True)
    
    resampled_data = latest_data.resample('1H').mean()
    resampled_data = resampled_data.iloc[:-1]
    resampled_data = resampled_data.reset_index()
    resampled_data.drop('timestamp_pengukuran', axis=1, inplace=True)
    resampled_data = resampled_data[model_name].values
    
    return resampled_data

models = {
    "suhu": load_model("model_temperature.h5"),
    "kelembapan_udara": load_model("model_humidity.h5"),
    "kelembapan_tanah": load_model("model_soilmoisture.h5")
}

n_steps = 10

def make_prediction(model, latest_data):
    x_input = latest_data.reshape((1, 10, 1))
    prediction_result = model.predict(x_input, verbose=0)
    return prediction_result[0]

def prediction(model_name):
    model = models[model_name]
    latest_data = get_latest_data(model_name)
    prediction_result = make_prediction(model, latest_data)
    return prediction_result


