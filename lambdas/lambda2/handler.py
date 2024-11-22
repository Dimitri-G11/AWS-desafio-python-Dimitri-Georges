import boto3
import pandas as pd
import pymysql
import os

# Inicializar cliente de SSM
ssm = boto3.client('ssm')

# Función para obtener un parámetro de SSM
def get_ssm_parameter(name):
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=True)  # WithDecryption es para parámetros SecureString
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Error al obtener parámetro de SSM: {e}")
        raise

# Recuperar las variables de entorno desde SSM
DB_HOST = get_ssm_parameter('/db_host')
DB_USER = get_ssm_parameter('/db_user')
DB_PASSWORD = get_ssm_parameter('/db_password')
DB_NAME = get_ssm_parameter('/db_name')

# Inicializar cliente de S3
s3 = boto3.client('s3')

# Tipos de vehículos de interés
VEHICLES = ['automovel', 'bicicleta', 'caminhao', 'moto', 'onibus']

def handler(event, context):
    try:
        # Extraer información del evento
        file_key = event['file_key']
        bucket_name = event['bucket_name']
        road_name = event['road_name']

        # Descargar el archivo CSV desde S3
        local_file = f"/tmp/{file_key}"
        s3.download_file(bucket_name, file_key, local_file)

        # Leer el archivo CSV con Pandas
        data = pd.read_csv(local_file)

        # Filtrar y calcular el número de muertos por vehículo
        results = []
        for vehicle in VEHICLES:
            filtered_data = data[data['vehicle_type'] == vehicle]
            deaths = filtered_data['deaths'].sum()
            results.append({
                "road_name": road_name,
                "vehicle": vehicle,
                "number_deaths": deaths
            })

        # Guardar los resultados en la base de datos
        save_to_database(results)

        # Retornar un resumen significativo
        return {
            "status": "success",
            "road_name": road_name,
            "metrics": results
        }
    except Exception as e:
        print(f"Error: {e}")
        raise

def save_to_database(results):
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    try:
        with connection.cursor() as cursor:
            # Verificar si las columnas existen, si no, crearlas
            cursor.execute("DESCRIBE accident_metrics")
            existing_columns = [column[0] for column in cursor.fetchall()]

            # Crear columnas si no existen
            if 'created_at' not in existing_columns:
                cursor.execute("ALTER TABLE accident_metrics ADD created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if 'road_name' not in existing_columns:
                cursor.execute("ALTER TABLE accident_metrics ADD road_name VARCHAR(255)")
            if 'vehicle' not in existing_columns:
                cursor.execute("ALTER TABLE accident_metrics ADD vehicle VARCHAR(255)")
            if 'number_deaths' not in existing_columns:
                cursor.execute("ALTER TABLE accident_metrics ADD number_deaths INT")

            # Insertar los resultados en la tabla
            for result in results:
                sql = """
                INSERT INTO accident_metrics (created_at, road_name, vehicle, number_deaths)
                VALUES (NOW(), %s, %s, %s)
                """
                cursor.execute(sql, (result['road_name'], result['vehicle'], result['number_deaths']))
            connection.commit()
    except Exception as e:
        print(f"Error al guardar en la base de datos: {e}")
        raise
    finally:
        connection.close()
