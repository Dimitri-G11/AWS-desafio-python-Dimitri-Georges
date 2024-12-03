import boto3
import requests
from botocore.exceptions import NoCredentialsError

s3 = boto3.client('s3')

def handler(event, context):
    try:
        url = event['csv_url']
        bucket_name = 'dimitris3'
        file_name = url.split('/')[-1]

        # Download do CSV
        response = requests.get(url)
        response.raise_for_status()
        
        # Upload para o S3
        s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=response.content
        )

        return {
            "statusCode": 200,
            "file_name": file_name,
            "bucket_name": bucket_name
        }
    except requests.exceptions.RequestException as e:
        return {"statusCode": 500, "message": f"Erro ao baixar o arquivo: {str(e)}"}
    except NoCredentialsError:
        return {"statusCode": 500, "message": "Credenciais inválidas para o S3"}
