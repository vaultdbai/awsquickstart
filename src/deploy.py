import boto3
import cfnresponse
import botocore
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource("s3")
vaultdb_deployment_region = os.environ["vaultdb_deployment_region"]
user_pool_id = os.environ["user_pool_id"]
source_bucket = os.environ["source_bucket"]
public_bucket = os.environ["public_bucket"]
data_bucket = os.environ["data_bucket"]


def lambda_handler(event, context):
    try:
        logger.info(f"event: {event}!")
        if event["RequestType"] == "Delete":
            delete_notification(public_bucket)
            for obj in s3.Bucket(public_bucket).objects.filter():
                s3.Object(public_bucket, obj.key).delete()
            try:
                for obj in s3.Bucket(data_bucket).objects.filter():
                    s3.Object(data_bucket, obj.key).delete()
            except Exception as e2:
                print(e2)
        elif event["RequestType"] == "Update":
            update_stack(data_bucket)
        elif event["RequestType"] == "Refresh":
            create_public_keys(data_bucket)
        else:
            logger.info("New files uploaded to the source bucket.")
            deploy_folder(source_bucket, public_bucket, folder_name="workbench/")
            create_pool_cofig(public_bucket)
            create_welcome_page(public_bucket)
            create_public_keys(data_bucket)

        if (event["RequestType"] == "Create" or event["RequestType"] == "Update") and (
            "LambdaArn" in event["ResourceProperties"]
        ):
            LambdaArn = event["ResourceProperties"]["LambdaArn"]
            add_notification(LambdaArn, public_bucket)

        cfnresponse.send(
            event,
            context,
            cfnresponse.SUCCESS,
            {"result": "success"},
            "CustomResourcePhysicalID",
        )
    except Exception as error:
        logger.error("Error Message: {}".format(error))
        cfnresponse.send(
            event,
            context,
            cfnresponse.FAILED,
            {"error": str(error)},
            "CustomResourcePhysicalID",
        )


def create_public_keys(data_bucket):
    import urllib.request

    logger.info("Creating JWT Public Keys Json!")
    keys_url = "https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json".format(
        vaultdb_deployment_region, user_pool_id
    )
    with urllib.request.urlopen(keys_url) as f:
        response = f.read()
    keysobject = s3.Object(bucket_name=data_bucket, key="jwks.json")
    keysobject.put(Body=response.decode("utf-8"))
    logger.info("Created JWT Public Keys!")


def create_welcome_page(public_bucket):
    logger.info("Creating Welcome page!")
    application_name = os.environ["application_name"]
    admin_email = os.environ["admin_email"]
    response = s3.meta.client.get_object(
        Bucket=source_bucket, Key="welcome_template.html"
    )
    welcomehtml = response["Body"].read().decode("utf-8")
    try:
        import pystache

        data = {"name": application_name, "email": admin_email}
        welcomehtml = pystache.render(welcomehtml, data)
    except:
        logger.info("template error")

    welcomeobject = s3.Object(bucket_name=public_bucket, key="index.html")
    welcomeobject.put(Body=welcomehtml, ContentType="text/html")
    logger.info("Created Welcome page!")


def update_stack(public_bucket):
    application_name = os.environ["application_name"]
    cloudformation_service_role_Arn = os.environ["cloudformation_service_role_Arn"]

    cf_client = boto3.client("cloudformation")
    response = cf_client.update_stack(
        StackName=application_name,
        UsePreviousTemplate=True,
        Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
        RoleARN=cloudformation_service_role_Arn,
        Parameters=[
            {
                "ParameterKey": "PrivateSubnetCIDR",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "PrimarySubnetAZ",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "ExistingVpcID",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "AdminEmail",
                "UsePreviousValue": True,
            },
        ],
    )
    logger.info(response)
    logger.info("Started Stack Update!")
    return response


def create_pool_cofig(public_bucket):
    application_name = os.environ["application_name"]
    user_pool_client_id = os.environ["user_pool_client_id"]
    identity_pool_id = os.environ["identity_pool_id"]
    public_bucket = os.environ["public_bucket"]

    logger.info(f"Creating workbench config file for pool {user_pool_id}!")

    data_string = f"""window.APPLICATION_NAME = "{application_name}";
    window.REGION= "{vaultdb_deployment_region}";
    window.USER_POOL_ID= "{user_pool_id}";
    window.USER_POOL_APP_CLIENT_ID= "{user_pool_client_id}";
    window.USER_IDENTITY_POOL_ID= "{identity_pool_id}";
    window.USER_BUCKET= "{public_bucket}";
    """

    object = s3.Object(bucket_name=public_bucket, key="workbench/config.js")
    object.put(Body=data_string)
    logger.info("Created workbench config file!")


def deploy_folder(source_bucket, public_bucket, folder_name, destination=None):
    try:
        for key in s3.meta.client.list_objects(
            Bucket=source_bucket, Prefix=folder_name
        )["Contents"]:
            file = key["Key"]
            if file == folder_name:
                continue
            logger.info(f"Copying file {file}")
            source = {"Bucket": source_bucket, "Key": file}
            if destination is not None:
                file = file.replace(folder_name, destination)
            response = s3.meta.client.copy(source, public_bucket, file)
        logger.info(f"Copied {folder_name} files!")
    except botocore.exceptions.ClientError as error:
        logger.error("There was an error copying the file to the destination bucket")
        logger.error("Error Message: {}".format(error))
    except botocore.exceptions.ParamValidationError as error:
        logger.error("Missing required parameters while calling the API.")
        logger.error("Error Message: {}".format(error))


def add_notification(LambdaArn, public_bucket):
    try:
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
    event = {'token':''}
    context = {'identity': {'cognito_identity_id':'', 'cognito_identity_pool_id':''}}
    lambda_handler(event, context)
