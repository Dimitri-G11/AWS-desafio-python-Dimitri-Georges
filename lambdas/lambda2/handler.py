import boto3
import pandas as pd
import os
from datetime import datetime

s3 = boto3.client('s3')

def handler(event, context):
    bucket = event['bucket_name']
    file_key = event['file_key']
    
    # Descargar archivo del S3
    response = s3.get_object(Bucket=bucket, Key=file_key)
    data = pd.read_csv(response['Body'])
    
    # Filtrar y calcular
    vehicles = ['automovel', 'bicicleta', 'caminhao', 'moto', 'onibus']
    filtered_data = data[data['vehicle'].isin(vehicles)]
    deaths_by_vehicle = filtered_data.groupby('vehicle')['number_deaths'].sum().reset_index()
    
    # Guardar en base de datos (simulado con impresión)
    for _, row in deaths_by_vehicle.iterrows():
        print({
            "created_at": datetime.now().isoformat(),
            "vehicle": row['vehicle'],
            "number_deaths": int(row['number_deaths']),
        })
    
    return {"status": "Processed", "details": deaths_by_vehicle.to_dict(orient='records')}
