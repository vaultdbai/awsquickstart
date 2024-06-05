<div align="center">
  <img src="https://www.vaultdb.ai/img/v-logo.png" height="120">
</div>
<br>

# VaultDB Data Platform

This repository contains the VaultDB ai platform aws quickstart templates.

## TODO:
### 1) Provide Update Button on Website to update and deploy lambda to kick off update to Stack

## Create Service Role

#### [![Launch stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=vaultdb-service-role&templateURL=https://vaultdb-web.s3.us-east-2.amazonaws.com/awsquickstart/service-role.yaml)

### AWS CLI Command to Create Cloud Formation Service Role

```
aws cloudformation create-stack --stack-name vaultdb-service-role --template-body file://service-role.yaml --capabilities CAPABILITY_NAMED_IAM
```
#### Use File from s3

```
aws cloudformation create-stack --stack-name vaultdb-service-role --template-body https://vaultdb-web.s3.us-east-2.amazonaws.com/awsquickstart/service-role.yaml --capabilities CAPABILITY_NAMED_IAM
```
#### Update Service Role

```
aws cloudformation update-stack --stack-name vaultdb-service-role --template-body file://service-role.yaml --capabilities CAPABILITY_NAMED_IAM
```
#### Use File from s3

```
aws cloudformation update-stack --stack-name vaultdb-service-role --template-body https://vaultdb-web.s3.us-east-2.amazonaws.com/awsquickstart/service-role.yaml --capabilities CAPABILITY_NAMED_IAM
```

## Create Private ECR

#### [![Launch stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=vaultdb-ecr&templateURL=https://vaultdb-web.s3.us-east-2.amazonaws.com/awsquickstart/ecr.yaml)

### AWS CLI Command to Create private ECR for Lambda

```
aws cloudformation create-stack --stack-name vaultdb-ecr --template-body file://ecr.yaml
```
#### Use File from s3

```
aws cloudformation create-stack --stack-name vaultdb-ecr --role-arn "arn:aws:iam::[AWS-ACCOUNT-NUMBER]:role/vaultdb_cloudformation_service_role" --template-body https://vaultdb-web.s3.us-east-2.amazonaws.com/awsquickstart/ecr.yaml --parameters ParameterKey="ECRRepoAlias",ParameterValue="vaultdbecr"
```
#### Update ECR

```
aws cloudformation update-stack --stack-name vaultdb-ecr --template-body file://ecr.yaml
```
#### Use File from s3

```
aws cloudformation update-stack --stack-name vaultdb-ecr --template-body https://vaultdb-web.s3.us-east-2.amazonaws.com/awsquickstart/ecr.yaml
```

### Push VaultDB Image to your ECR
#### pull the docker image:
```
docker pull public.ecr.aws/i2q7a2j7/vaultdb:lambda
```
#### create a target image tag that refers to the source image:
```
docker tag public.ecr.aws/i2q7a2j7/vaultdb:lambda [YOUR_AWS_ACCOUNT_ID].dkr.ecr.[AWS-REGION-WHERE-YOU-WANT-TO-DEPLOY-VAULTDB].amazonaws.com/vaultdb:lambda
```
#### Authenticate
```
aws ecr get-login-password --region [AWS-REGION-WHERE-YOU-WANT-TO-DEPLOY-VAULTDB] | docker login --username AWS --password-stdin [YOUR_AWS_ACCOUNT_ID].dkr.ecr.[AWS-REGION-WHERE-YOU-WANT-TO-DEPLOY-VAULTDB].amazonaws.com
```
####  push the image
```
docker push [YOUR_AWS_ACCOUNT_ID].dkr.ecr.[AWS-REGION-WHERE-YOU-WANT-TO-DEPLOY-VAULTDB].amazonaws.com/vaultdb:lambda
```

## Deploy VaultDB Instance

### Note: Make sure to pick the vaultdb_cloudformation_service_role

### [![Launch stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=dev-test-prod&templateURL=https://vaultdb-web.s3.us-east-2.amazonaws.com/awsquickstart/vaultdb.yaml)

### AWS CLI Command to Create VaultDB Instance
```
aws cloudformation create-stack --stack-name [APPLICATION-STACK-NAME] --role-arn "arn:aws:iam::[AWS-ACCOUNT-NUMBER]:role/vaultdb_cloudformation_service_role" --template-url https://vaultdb-web.s3.us-east-2.amazonaws.com/awsquickstart/vaultdb.yaml --parameters ParameterKey="AdminEmail",ParameterValue="[APPLICATION-ADMIN-EMAIL-ADDRESS]" ParameterKey="PrimarySubnetAZ",ParameterValue="us-east-1a" ParameterKey="CidrBlock",ParameterValue="10.0.0.0/16" ParameterKey="PrivateSubnetCIDR",ParameterValue="10.0.20.0/24" ParameterKey="BucketName",ParameterValue="vaultdb-web" --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND
```
    
#### command Parameter Descriptions:--
    APPLICATION-STACK-NAME
        Pick a Uniquename for your installation and append test/dev/uat/prod etc to diffrentiate between different environments.
    AWS-ACCOUNT-NUMBER
        AWS Account number
    APPLICATION-ADMIN-EMAIL-ADDRESS
        this email will receive the user passwords and instructions on how to start using VAULTDB ai platform.
    VPC-ID
        Provide the VPC ID if you have one and wants to use that otherwise remove the parameter all together or provide empty value
    VPC-CIDR-BLOCK
        10.0.0.0/16

## Delete/ Uninstall

aws cloudformation delete-stack --stack-name [APPLICATION-STACK-NAME]

## Example

### create

```
aws cloudformation update-stack --stack-name dev --role-arn "arn:aws:iam::[AWS-ACCOUNT-NUMBER]:role/vaultdb_cloudformation_service_role" --template-url https://vaultdb-hosted-content.s3.us-east-2.amazonaws.com/awsquickstart/vaultdb.yaml --parameters ParameterKey="AdminEmail",ParameterValue="vaultdb@outlook.com" ParameterKey="PrimarySubnetAZ",ParameterValue="us-east-1a" ParameterKey="ExistingVpcID",ParameterValue="vpc-053032fa3ede15b8b" ParameterKey="PrivateSubnetCIDR",ParameterValue="172.31.200.0/20" ParameterKey="BucketName",ParameterValue="vaultdb-hosted-content" --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND
```

### Delete/ Uninstall

aws cloudformation delete-stack --stack-name dev

## License

All Images and Text copyright VaultDB.ai LLC
