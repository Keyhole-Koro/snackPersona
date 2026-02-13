import os
import boto3
from botocore.config import Config

def get_dynamodb_resource():
    """
    Returns a configured DynamoDB resource.
    Supports LocalStack via AWS_ENDPOINT_URL.
    """
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    
    config = Config(
        retries = {'max_attempts': 3, 'mode': 'standard'}
    )

    if endpoint_url:
        return boto3.resource(
            'dynamodb',
            endpoint_url=endpoint_url,
            config=config,
            # Dummy credentials for LocalStack
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1'
        )
    else:
        return boto3.resource('dynamodb', config=config)

def get_table():
    dynamodb = get_dynamodb_resource()
    table_name = os.getenv("DYNAMODB_TABLE", "SnackTable")
    return dynamodb.Table(table_name)
