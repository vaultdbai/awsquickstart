# Imports
import os
import cfnresponse
import logging
import json
import datetime
import duckdb
import boto3
from typing import Any, Dict, Optional
from botocore.client import BaseClient
from duckdb import DuckDBPyConnection

import tracemalloc

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG) # Very verbose

application_name = os.environ['application_name'] if "application_name" in os.environ else "test"
account_id = os.environ['account_id'] if "account_id" in os.environ else "440955376164"
commitlog_directory = os.environ['commitlog_directory'] if "commitlog_directory" in os.environ else "/tmp"
public_bucket = os.environ['public_bucket'] if "public_bucket" in os.environ else None
data_store = os.environ['data_store'] if "data_store" in os.environ else None
app_client_id = os.environ['user_pool_client_id'] if "user_pool_client_id" in os.environ else None
memory_limit = int(os.environ['memory_limit']) if "memory_limit" in os.environ else 2048
TIMEOUT_SECONDS =  int(os.environ['TIMEOUT_SECONDS']) - 30 if "TIMEOUT_SECONDS" in os.environ else 290
threads = os.environ['threads'] if "threads" in os.environ else '3'
AWS_DEFAULT_REGION =  os.environ['AWS_DEFAULT_REGION'] if "AWS_DEFAULT_REGION" in os.environ else f'us-east-1'
AWS_LAMBDA_FUNCTION_NAME =  os.environ['AWS_LAMBDA_FUNCTION_NAME'] if "AWS_LAMBDA_FUNCTION_NAME" in os.environ else f'{application_name}-merge-data'

START_TIME = datetime.datetime.now()

def lambda_handler(event, context):
    logger.info(f'event: {event}')
    try:
        delete_notification(public_bucket)
        if 'Records' in event:
            for record in event['Records']:
                source_bucket = record['s3']['bucket']['name']
                logger.info(f'source_bucket: {source_bucket}')
                file_key = record['s3']['object']['key']
                logger.info(f'file_key: {file_key}')
                preferred_role = file_key.split('/')[-4]    
                logger.info(f'preferred_role: {preferred_role}')
                database_name = file_key.split('/')[-2]
                logger.info(f'database_name: {database_name}')
                db_path = f"{commitlog_directory}/{database_name}.db"

                merge_database(source_bucket, file_key, preferred_role, database_name, db_path)

        return force_merge()        
    except Exception as ex:
        logger.error(ex)
        return send_response(event, context, cfnresponse.FAILED, {'error':str(ex)})
    finally:
        LambdaArn = f"arn:aws:lambda:{AWS_DEFAULT_REGION}:{account_id}:function:{AWS_LAMBDA_FUNCTION_NAME}" 
        add_notification(LambdaArn, public_bucket)        

def force_merge():
    # starting the monitoring
    logger.debug(f'TIMEOUT IN SECONDS: {TIMEOUT_SECONDS}')
    tracemalloc.start()
    logger.debug(f"Memory used: {tracemalloc.get_traced_memory()}")
    # Create an S3 client
    s3_client = boto3.client("s3")

    # Initiate pagination to handle potential large number of objects
    paginator = s3_client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(
        Bucket=public_bucket, Prefix="merge_queue/", Delimiter="/"
    )    
    for page in page_iterator:
        # Check if 'CommonPrefixes' key exists, indicating folders
        if "CommonPrefixes" in page:
            for prefix in page["CommonPrefixes"]:
                folder_name = prefix["Prefix"][:-1]  # Remove trailing slash
                logger.debug(f'folder: {folder_name}')
                logger.debug(f"Memory used: {tracemalloc.get_traced_memory()}")
                
                role_paginator = s3_client.get_paginator("list_objects_v2")
                role_page_iterator = role_paginator.paginate(
                    Bucket=public_bucket, Prefix=f"{folder_name}/", Delimiter="/"
                )
                for role_page in role_page_iterator:
                    if "CommonPrefixes" in role_page:
                        for role_prefix in role_page["CommonPrefixes"]:
                            role_key = role_prefix["Prefix"][:-1]  # Remove trailing slash
                            preferred_role = role_key.split('/')[-1]  # Remove trailing slash                            

                            # Define the payload to send to the target Lambda (optional)
                            database_paginator = s3_client.get_paginator("list_objects_v2")
                            database_page_iterator = database_paginator.paginate(
                                Bucket=public_bucket, Prefix=f"{folder_name}/{preferred_role}/master/", Delimiter="/"
                            )
                            for database_page in database_page_iterator:                
                                if "CommonPrefixes" in database_page:
                                    for database_prefix in database_page["CommonPrefixes"]:
                                        file_key = database_prefix["Prefix"][:-1]  # Remove trailing slash
                                        database_name = file_key.split('/')[-1]  # Remove trailing slash                            
                                        logger.debug(f'file_key: {file_key}')
                                        logger.debug(f"Before Merge start Memory used: {tracemalloc.get_traced_memory()}")                            
                                        merge_database(public_bucket, f"{file_key}/load.sql", preferred_role, database_name, f"{commitlog_directory}/{database_name}.db")
                                        logger.debug(f"After Merge Done Memory used: {tracemalloc.get_traced_memory()}") 
                                        finish = datetime.datetime.now() - START_TIME
                                        logger.debug(f'number of seconds elapsed: {finish.seconds}')
                                        if finish.seconds >= TIMEOUT_SECONDS:
                                            return send_response(event, context, cfnresponse.SUCCESS, {'result':'success'})
                            
    return send_response(event, context, cfnresponse.SUCCESS, {'result':'success'})

def merge_database(source_bucket: str, file_key: str, preferred_role: str, database_name: str, db_path: str) -> None:
    try:
        with get_db_connection(db_path, preferred_role) as connection:
            set_db_config(connection)
            s3_client: BaseClient = boto3.client('s3')
            
            execute_schema(s3_client, source_bucket, file_key, connection)
            execute_load(s3_client, source_bucket, file_key, connection)
            
            perform_merge(connection, database_name)
            connection.close()            
        archive_and_cleanup(s3_client, source_bucket, file_key)
        upload_to_s3(db_path, database_name)        
    except Exception as ex:
        logger.error(f"Error in merge_database: {ex}")
        raise

def get_db_connection(db_path: str, role: str) -> DuckDBPyConnection:
    return duckdb.connect(db_path, False, config={'autoinstall_known_extensions': 'true'}, role=role)

def set_db_config(connection: DuckDBPyConnection) -> None:
    connection.execute(f"SET memory_limit='{int(memory_limit/1024)}GB';")
    connection.execute(f"SET threads='{threads}';")
    connection.execute(f"SET temp_directory='/tmp';")

def execute_schema(s3_client: BaseClient, source_bucket: str, file_key: str, connection: DuckDBPyConnection) -> None:
    schema_key = file_key.replace("load.sql", "schema.sql")
    execute_sql_from_s3(s3_client, source_bucket, schema_key, connection)
    logger.debug('schema executed')

def execute_load(s3_client: BaseClient, source_bucket: str, file_key: str, connection: DuckDBPyConnection) -> None:
    execute_sql_from_s3(s3_client, source_bucket, file_key, connection)
    logger.debug('load executed')

def execute_sql_from_s3(s3_client: BaseClient, bucket: str, key: str, connection: DuckDBPyConnection) -> int:
    response: Dict[str, Any] = s3_client.get_object(Bucket=bucket, Key=key)
    file_content: Any = response['Body'].iter_lines()
    counter: int = 0
    for line in file_content:
        stmt: str = line.decode('utf-8').strip()
        if stmt:
            logger.info(f'Executing Statement: {line}')             
            if ("CREATE SCHEMA" in stmt and "IF NOT EXISTS" not in stmt and "ON CONFLICT" not in stmt):
                stmt = stmt.replace(";", " IF NOT EXISTS;")
            elif ("CREATE " in stmt and " REPLACE " not in stmt):
                stmt = stmt.replace("CREATE ", "CREATE OR REPLACE ")
            stmt_result = connection.execute(stmt)
            counter+=1
            logger.info(f'Statement Result: {stmt_result.fetchdf()}')    

    return counter

def perform_merge(connection: DuckDBPyConnection, database_name: str) -> None:
    connection.execute(f"PRAGMA enable_data_inheritance;")
    connection.execute(f"set http_retries=3;")
    logger.debug(f"Starting Merge database process: {tracemalloc.get_traced_memory()}")
    connection.execute(f"MERGE DATABASE {database_name};")
    logger.debug('merge executed')
    connection.execute('BEGIN TRANSACTION;')
    connection.execute(f"TRUNCATE DATABASE {database_name};")
    connection.execute('COMMIT;')
    connection.execute('VACUUM ANALYZE;')    
    logger.debug('data truncated')

def archive_and_cleanup(s3_client: BaseClient, source_bucket: str, file_key: str) -> None:
    head, tail = os.path.split(file_key)
    logger.info(f'head: {head}')
    paginator = s3_client.get_paginator('list_objects_v2')
    result = paginator.paginate(Bucket=source_bucket, Prefix=head)
    for page in result:
        if "Contents" in page:
            for key in page[ "Contents" ]:
                copy_source = {
                    'Bucket': source_bucket,
                    'Key': key[ "Key" ]
                    }
                logger.info(f'copy_source: {copy_source}')
                logger.debug(f"Memory used: {tracemalloc.get_traced_memory()}")                            
                s3_client.copy(copy_source, data_store, f"archived/{key[ 'Key' ]}", ExtraArgs=None, Callback=None, SourceClient=None, Config=None)
                logger.debug(f"Memory used: {tracemalloc.get_traced_memory()}")                            
                del_response = s3_client.delete_object(Bucket=source_bucket, Key=key[ "Key" ])
                if del_response["ResponseMetadata"]["HTTPStatusCode"]!=204:
                    logger.error(f'del_response: {del_response}')
                    #return send_response(event, context, cfnresponse.FAILED, {'error':f"couldn't archive file {key[ 'Key' ]}"})     
    logger.debug(f"Memory used: {tracemalloc.get_traced_memory()}")                            

def upload_to_s3(db_path: str, database_name: str) -> None:
    s3 = boto3.resource("s3")
    s3.meta.client.upload_file(Filename=db_path, Bucket=public_bucket, Key=f"catalogs/{database_name}.db")
    logger.debug(f'copied {database_name} database file to s3 ')            
    logger.debug(f"Memory used: {tracemalloc.get_traced_memory()}")                            

def send_response(event, context, result, message):
    if "ResponseURL" in event:
        cfnresponse.send(event, context, result, message)
    elif result==cfnresponse.FAILED:
        return {"result":"Error", "message":message}
    else:
        return {"result":"Success", "message":message}

def add_notification(LambdaArn, public_bucket):
    try:
        s3 = boto3.resource("s3")
        bucket_notification = s3.BucketNotification(public_bucket)
        response = bucket_notification.put(
            NotificationConfiguration={
                "LambdaFunctionConfigurations": [
                    {
                        "LambdaFunctionArn": LambdaArn,
                        "Events": ["s3:ObjectCreated:*"],
                        "Filter": {
                            "Key": {
                                "FilterRules": [
                                    {"Name": "prefix", "Value": "merge_queue"},
                                    {"Name": "suffix", "Value": "load.sql"},
                                ]
                            }
                        },
                    }
                ]
            }
        )
        logger.info(response)
    except Exception as error:
        logger.error("There was an error add_notification to the  bucket")
        logger.error("Error Message: {}".format(error))
        logger.error("Error response: {}".format(error.response))


def delete_notification(public_bucket):
    try:
        s3 = boto3.resource("s3")
        bucket_notification = s3.BucketNotification(public_bucket)
        response = bucket_notification.put(NotificationConfiguration={})
        logger.info(response)
    except Exception as error:
        logger.error("There was an error delete_notification to the  bucket")
        logger.error("Error Message: {}".format(error))
        logger.error("Error response: {}".format(error.response))


# the following is useful to make this script executable in both
# AWS Lambda and any other local environments
if __name__ == '__main__':
    # for testing locally you can enter the JWT ID Token here
    event = {'Records': [{'eventVersion': '2.1', 'eventSource': 'aws:s3', 'awsRegion': 'us-east-2', 'eventTime': '2024-04-18T22:40:20.133Z', 'eventName': 'ObjectCreated:CompleteMultipartUpload', 'userIdentity': {'principalId': 'AWS:AROAWNKX5CISM44TJDRCX:CognitoIdentityCredentials'}, 'requestParameters': {'sourceIPAddress': '67.84.103.238'}, 'responseElements': {'x-amz-request-id': '81G2K850C473HHHY', 'x-amz-id-2': 'oyi6lFHMK86UMhcg2+XqvSgTBC7kTPUmcHsF0/NGKvVdikBD4x6AmqZLLqO3UPAdjcdqsEOnBrACSaQVefsHXa7EqJaniNYj'}, 's3': {'s3SchemaVersion': '1.0', 'configurationId': 'OTI4OTEyNTktN2Y5OC00MDhhLTg5NDMtMmZjYWU2ZDEyOWEy', 'bucket': {'name': 'dev-public-storage-440955376164', 'ownerIdentity': {'principalId': 'A1N7AZ0AQHW4H'}, 'arn': 'arn:aws:s3:::dev-public-storage-440955376164'}, 'object': {'key': 'merge_queue/vaultdb/master/dev/load.sql', 'size': 270, 'eTag': '492b10a9a06f9e1547f5e1897a9f45fa-1', 'sequencer': '006621A153C7FC847A'}}}]}
    context = {'identity': {'cognito_identity_id':'', 'cognito_identity_pool_id':''}}
    lambda_handler([""], context)
    #lambda_handler(event, context)
    