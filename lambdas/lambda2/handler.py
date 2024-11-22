import boto3
import pandas as pd
import pymysql

s3 = boto3.client('s3')

VEHICLES = ['automovel', 'bicicleta', 'caminhao', 'moto', 'onibus']

def handler(event, context):
    try:
        # Extraer información del evento
        file_key = event['file_key']
        bucket_name = event['bucket_name']
        road_name = event['road_name']

        # Descargar el archivo CSV desde S3
        local_file = f"/tmp/{file_key.split('/')[-1]}"
        s3.download_file(bucket_name, file_key, local_file)

        # Leer el archivo CSV
        data = pd.read_csv(local_file)

        # Calcular el número de muertos por tipo de vehículo
        results = []
        for vehicle in VEHICLES:
            filtered_data = data[data['vehicle_type'] == vehicle]
            deaths = filtered_data['deaths'].sum()
            results.append({
                "road_name": road_name,
                "vehicle": vehicle,
                "number_deaths": deaths
            })

        # Guardar resultados en la base de datos
        save_to_database(results)

        return {
            "status": "success",
            "metrics": results
        }

    except Exception as e:
        print(f"Error: {e}")
        raise

def save_to_database(results):
    connection = pymysql.connect(
        host=os.environ['DB_HOST'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        database=os.environ['DB_NAME']
    )

    try:
        with connection.cursor() as cursor:
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
