import boto3
import json
import psycopg2
from datetime import datetime
import csv


ssm = boto3.client('ssm')

def get_ssm_parameter(name):
    
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=True)
        return json.loads(response['Parameter']['Value']) 
    except Exception as e:
        print(f"Erro ao recuperar parâmetro do SSM: {e}")
        raise

def create_table_if_not_exists(cursor):
   
    create_table_query = """
    CREATE TABLE IF NOT EXISTS accidents_data (
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMP NOT NULL,
        road_name VARCHAR(255) NOT NULL,
        vehicle VARCHAR(50) NOT NULL,
        number_deaths INT NOT NULL
    )
    """
    cursor.execute(create_table_query)

def handler(event, context):
    try:
       
        db_credentials = get_ssm_parameter('/db_secrets')  

        bucket_name = event['bucket_name']
        file_name = event['file_name']
        print(f"Processando arquivo {file_name} do bucket {bucket_name}")

        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=bucket_name, Key=file_name)
        csv_content = response['Body'].read().decode('utf-8')

        csv_reader = csv.DictReader(csv_content.splitlines())
        vehicles_of_interest = ['automovel', 'bicicleta', 'caminhao', 'moto', 'onibus']
        processed_data = []

        for row in csv_reader:
            vehicle = row['vehicle'].lower()
            if vehicle in vehicles_of_interest:
                processed_data.append({
                    "created_at": datetime.now(),
                    "road_name": row['road_name'],
                    "vehicle": vehicle,
                    "number_deaths": int(row['number_deaths']),
                })

      
        conn = psycopg2.connect(
            host=db_credentials['host'],
            dbname=db_credentials['dbname'],
            user=db_credentials['username'],
            password=db_credentials['password'],
            port=5432
        )
        cursor = conn.cursor()

        
        create_table_if_not_exists(cursor)

        
        insert_query = """
            INSERT INTO accidents_data (created_at, road_name, vehicle, number_deaths)
            VALUES (%s, %s, %s, %s)
        """
        for data in processed_data:
            cursor.execute(insert_query, (
                data['created_at'],
                data['road_name'],
                data['vehicle'],
                data['number_deaths']
            ))

        # Commit e fechamento da conexão
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "statusCode": 200,
            "message": f"Dados inseridos com sucesso. Total de registros: {len(processed_data)}",
            "file_name": file_name
        }
    except Exception as e:
        print(f"Erro: {e}")
        return {
            "statusCode": 500,
            "message": f"Erro ao processar os dados: {str(e)}"
        }
