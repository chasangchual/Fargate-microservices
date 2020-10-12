
## Project spectrum

This is a CDK project including following components:

- VPC Creation
- ECS cluster Fargate type

## CDK development environment:

```bash
CDK_VERSION=v1.66.0
npm install -g aws-cdk@${CDK_VERSION}
cdk --version
python3 -m venv env
source env/bin/activate
pip install --upgrade -r requirements.txt
```

## CDK Deployment procedure

```shell
$ cdk deploy 
```

or with custom environment:

```shell
$ cdk deploy -c domain_name=mydomain -c env=prd
```

or every stack seperately:

```shell
$ cdk deploy vpc-stack 
```

## Useful commands

-   `cdk boostrap` cdk bootstrap is a tool in the AWS CDK command-line interface responsible for populating a given environment with resources required by the CDK to perform deployments into that environment.
-   `cdk deploy` deploy this stack to your default AWS account/region
-   `cdk diff` compare deployed stack with current state
-   `cdk synth` emits the synthesized CloudFormation template
