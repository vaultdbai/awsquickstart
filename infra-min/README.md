## Setup VaultDB Infrastructure 

1) Create VPC if Not Exists

  awsv2 cloudformation create-stack --stack-name vaultdb-vpc --template-body file://vpc.yaml --parameters file://vpc_parameters.json

2) CodeArtifact repo

  awsv2 cloudformation create-stack --stack-name vaultdb-codeartifact --template-body file://codeartifact_repository.yaml --parameters file://codeartifact_parameters.json


https://s3.amazonaws.com/vaultdb-hosted-content/awsquickstart/infra/infra.yaml

awsv2 cloudformation create-stack --stack-name vaultdb-vpc --template-body file://vpc.yaml --parameters file://parameters.json