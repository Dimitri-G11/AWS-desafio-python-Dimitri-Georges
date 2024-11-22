import boto3
import requests
import yaml
import pandas as pd

# Inicializar clientes de S3 y SSM
s3 = boto3.client('s3')
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
S3_BUCKET_NAME = get_ssm_parameter('/s3_bucket_name')

def handler(event, context):
    try:
        # Cargar enlaces desde el archivo link.yml
        with open("link.yml", "r") as file:
            links = yaml.safe_load(file)

        # Validar el evento recibido
        road_name = event.get('road_name')
        if not road_name or road_name not in links:
            raise ValueError("El nombre de la carretera es inválido o no está definido.")

        # Descargar archivo desde el enlace
        url = links[road_name]
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Error al descargar el archivo desde {url}")
        
        # Leer el CSV descargado
        csv_data = pd.read_csv(pd.compat.StringIO(response.text))

        # Realizar transformaciones específicas (según los requisitos)
        processed_data = csv_data.drop(columns=['column_to_remove'], errors='ignore')  # Ajustar según el CSV
        processed_data['processed_at'] = pd.Timestamp.now()  # Agregar marca de tiempo del procesamiento

        # Guardar CSV transformado localmente
        local_file = f"/tmp/{road_name}_processed.csv"
        processed_data.to_csv(local_file, index=False)

        # Subir archivo procesado al bucket S3
        file_key = f"{road_name}_processed.csv"
        s3.upload_file(local_file, S3_BUCKET_NAME, file_key)

        # Retornar información para Lambda 2
        return {
            "file_key": file_key,
            "bucket_name": S3_BUCKET_NAME,
            "road_name": road_name,
            "record_count": len(processed_data)  # Número de registros procesados
        }
    except Exception as e:
        print(f"Error: {e}")
        raise
