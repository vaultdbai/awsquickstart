# Imports
import os
import cfnresponse
import logging
import json
import duckdb
import boto3

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG) # Very verbose

application_name = os.environ['application_name'] if "application_name" in os.environ else ""
commitlog_directory = os.environ['commitlog_directory'] if "commitlog_directory" in os.environ else "/tmp"
public_bucket = os.environ['public_bucket'] if "public_bucket" in os.environ else None
data_store = os.environ['data_store'] if "data_store" in os.environ else None
app_client_id = os.environ['user_pool_client_id'] if "user_pool_client_id" in os.environ else None


def lambda_handler(event, context):
    logger.info(f'event: {event}')

    try:
        # Create a Boto3 S3 client
        s3_client = boto3.client('s3')

        for record in event['Records']:
            source_bucket = record['s3']['bucket']['name']
            logger.info(f'source_bucket: {source_bucket}')
            file_key = record['s3']['object']['key']
            logger.info(f'file_key: {file_key}')
            preferred_role = file_key.split('/')[1]    
            logger.info(f'preferred_role: {preferred_role}')
            database_name = file_key.split('/')[-2]
            logger.info(f'database_name: {database_name}')
            db_path = f"{commitlog_directory}/{database_name}.db"

            if not os.path.isfile(db_path):
                return send_response(event, context, cfnresponse.FAILED, {'error':f"Catalog {database_name} does not exist!"})
                
            # connect to database
            connection = duckdb.connect(db_path, False, preferred_role, config={'autoinstall_known_extensions' : 'true'})
            
            counter = execute(s3_client, source_bucket, file_key.replace("load.sql", "schema.sql"), connection)
            
            counter = execute(s3_client, source_bucket, file_key, connection)

            if counter:
                connection.execute(f"PRAGMA enable_data_inheritance;")
                stmt_result = connection.execute(f"MERGE DATABASE {database_name};")
                logger.info(f'Statement Result: {stmt_result.fetchdf()}')
                connection.execute(f"TRUNCATE DATABASE {database_name};")
                connection.close()
                # CLose and reopen to make sure we are not carying data to s3
                connection = duckdb.connect(db_path, False, "vaultdb")   
                connection.close()         
                s3 = boto3.resource("s3")
                s3.meta.client.upload_file(Filename=db_path, Bucket=public_bucket, Key=f"catalogs/{database_name}.db")
                logger.debug(f'copied {database_name} database file to s3 ')    

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
                        s3_client.copy(copy_source, source_bucket, f"archived/{key[ 'Key' ]}", ExtraArgs=None, Callback=None, SourceClient=None, Config=None)
                        del_response = s3_client.delete_object(Bucket=source_bucket, Key=key[ "Key" ])
                        if del_response["ResponseMetadata"]["HTTPStatusCode"]!="204":
                            logger.error(f'del_response: {del_response}')
                            return send_response(event, context, cfnresponse.FAILED, {'error':f"couldn't archive file {key[ 'Key' ]}"})
                        
        return send_response(event, context, cfnresponse.SUCCESS, {'result':'success'})
    except Exception as ex:
        logger.error(ex)
        return send_response(event, context, cfnresponse.FAILED, {'error':str(ex)})

def execute(s3_client, source_bucket, file_key, connection):
    # Retrieve the object from S3
    response = s3_client.get_object(Bucket=source_bucket, Key=file_key)            
    # Read the file content line by line
    file_content = response['Body'].iter_lines()
    if not file_content:
        return send_response(event, context, cfnresponse.FAILED, {'error':"empty file contents!"})

    connection.execute(f"PRAGMA disable_data_inheritance;")
    # Process each line of the file
    counter = 0
    for line in file_content:
        stmt = line.decode('utf-8').strip()
        if stmt:
            logger.info(f'Executing Statement: {line}')
            if ("CREATE " in stmt and " REPLACE " not in stmt):
                stmt = stmt.replace("CREATE ", "CREATE OR REPLACE ")
            stmt_result = connection.execute(stmt)
            counter+=1
            logger.info(f'Statement Result: {stmt_result.fetchdf()}')    

    return counter

def send_response(event, context, result, message):
    if "ResponseURL" in event:
        cfnresponse.send(event, context, result, message)
    elif result==cfnresponse.FAILED:
        return {"result":"Error", "message":message}
    else:
        return {"result":"Success", "message":message}

# the following is useful to make this script executable in both
# AWS Lambda and any other local environments
if __name__ == '__main__':
    # for testing locally you can enter the JWT ID Token here
    event = {'token':''}
    context = {'identity': {'cognito_identity_id':'', 'cognito_identity_pool_id':''}}
    lambda_handler(event, context)
    