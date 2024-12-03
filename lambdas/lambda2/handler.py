import boto3
import json
import psycopg2
from psycopg2.extras import execute_values
import csv

# Inicializar clientes AWS
ssm = boto3.client('ssm')
secrets_client = boto3.client('secretsmanager')

def get_ssm_parameter(name):
    """
    Recupera um parâmetro do SSM Parameter Store.
    """
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Erro ao recuperar parâmetro do SSM: {e}")
        raise

def get_db_credentials(secret_id):
    """
    Recupera credenciais do banco de dados do Secrets Manager.
    """
    try:
        response = secrets_client.get_secret_value(SecretId=secret_id)
        secret = json.loads(response['SecretString'])
        return secret  # Retorna o dicionário completo com credenciais
    except Exception as e:
        print(f"Erro ao recuperar segredo {secret_id}: {e}")
        raise

def handler(event, context):
    try:
        db_secret_id = get_ssm_parameter('db_secret_id') 

        db_credentials = get_db_credentials(db_secret_id)
        print(f"Credenciais do banco recuperadas: {db_credentials}")

        bucket_name = event['bucket_name']
        file_name = event['file_name']
        print(f"Processando arquivo: {file_name} no bucket {bucket_name}")

        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=bucket_name, Key=file_name)
        csv_content = response['Body'].read().decode('utf-8')

        # Processar CSV
        csv_reader = csv.reader(csv_content.splitlines())
        header = next(csv_reader)  
        rows = list(csv_reader)   

        conn = psycopg2.connect(
            host=db_credentials['host'],
            dbname=db_credentials['dbname'],
            user=db_credentials['username'],
            password=db_credentials['password'],
            port=db_credentials.get('port', 5432)
        )
        cursor = conn.cursor()

        # Inserir dados no banco
        table_name = "your_table_name"  
        columns = ", ".join(header)
        insert_query = f"INSERT INTO {table_name} ({columns}) VALUES %s"
        execute_values(cursor, insert_query, rows)

        # Commit e fechamento da conexão
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "statusCode": 200,
            "message": "Dados inseridos no banco de dados com sucesso.",
            "file_name": file_name,
            "record_count": len(rows)
        }
    except Exception as e:
        print(f"Erro: {e}")
        return {
            "statusCode": 500,
            "message": f"Erro ao processar os dados: {str(e)}"
        }
