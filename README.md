
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

```
cdk synth
cdk deploy vpc-stack --profile "my-profile"
cdk deploy ecs-stack --profile "my-profile"
```