from aws_cdk import(
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_s3_deployment as s3_deploy,
    aws_cloudfront as cfn,
    aws_iam as iam,
    core
)

class S3Stack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        prj_name = self.node.try_get_context("project_name")
        env_name = self.node.try_get_context("env")

        account_id = core.Aws.ACCOUNT_ID

        #To Store Frontend app

        FlaskFrontendBucket = s3.Bucket(self, 'FlaskFrontendWebsite',
            #access_control=s3.BucketAccessControl.BUCKET_OWNER_FULL_CONTROL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            bucket_name=account_id+'-'+env_name+'-frontend',
            access_control=s3.BucketAccessControl.PUBLIC_READ,
            # block_public_access=s3.BlockPublicAccess(
            #     block_public_acls=True,
            #     block_public_policy=True,
            #     ignore_public_acls=True,
            #     restrict_public_buckets=True,
            # ),
            removal_policy=core.RemovalPolicy.DESTROY
        )
        
        policy_statement = iam.PolicyStatement(
            actions=["s3:GetObject"],
            resources=[f"{FlaskFrontendBucket.bucket_arn}/*"],
        )

        policy_statement.add_any_principal()

        static_site_policy_document = iam.PolicyDocument(
            statements=[policy_statement]
        )

        FlaskFrontendBucket.add_to_resource_policy(policy_statement)

        
        # The Origin Access Identity is a way to allow CloudFront
        # Access to the Website Bucket
        origin_access_identity = cfn.OriginAccessIdentity(
            self, "OriginAccessIdentity",
            comment="Allows Read-Access from CloudFront"
        )

        # We tell the website bucket to allow access from CloudFront
        FlaskFrontendBucket.grant_read(origin_access_identity)

        s3_deploy.BucketDeployment(self, "DeployFlaskFrontendWebsite",
            sources=[s3_deploy.Source.asset("./static")],
            destination_bucket=FlaskFrontendBucket,
            destination_key_prefix="web/static"
        )

        core.CfnOutput(self, 'S3FlaskFrontendExport',
            value = FlaskFrontendBucket.bucket_name,
            export_name='FlaskFrontendBucket'
        )