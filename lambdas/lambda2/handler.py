import boto3
import pandas as pd
import pymysql
import os

# Inicializar cliente de S3
s3 = boto3.client('s3')

# Configuração do banco de dados RDS
DB_HOST = os.environ['DB_HOST']  # Endpoint do RDS (sem o "http://")
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_NAME']

# Tipos de veículos de interesse
VEHICLES = ['automovel', 'bicicleta', 'caminhao', 'moto', 'onibus']

def handler(event, context):
    try:
        # Extraindo informações do evento
        file_key = event['file_key']
        bucket_name = event['bucket_name']
        road_name = event['road_name']

        # Baixando o arquivo CSV do S3
        local_file = f"/tmp/{file_key}"
        s3.download_file(bucket_name, file_key, local_file)

        # Lendo o CSV com Pandas
        data = pd.read_csv(local_file)

        # Filtrando e calculando o número de mortos por veículo
        results = []
        for vehicle in VEHICLES:
            filtered_data = data[data['vehicle_type'] == vehicle]
            deaths = filtered_data['deaths'].sum()
            results.append({
                "road_name": road_name,
                "vehicle": vehicle,
                "number_deaths": deaths
            })

        # Salvando os resultados no banco de dados
        save_to_database(results)

        # Retornando um resumo significativo
        return {
            "status": "success",
            "road_name": road_name,
            "metrics": results
        }
    except Exception as e:
        print(f"Error: {e}")
        raise

def save_to_database(results):
    # Conectando ao banco de dados RDS
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    try:
        with connection.cursor() as cursor:
            # Inserindo os resultados na tabela
            for result in results:
                sql = """
                INSERT INTO accident_metrics (created_at, road_name, vehicle, number_deaths)
                VALUES (NOW(), %s, %s, %s)
                """
                cursor.execute(sql, (result['road_name'], result['vehicle'], result['number_deaths']))
            connection.commit()
    finally:
        connection.close()
