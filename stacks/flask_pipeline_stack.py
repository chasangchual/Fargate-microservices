from aws_cdk import (
    aws_ecr,
    core,
    aws_codecommit,
    aws_codebuild,
    aws_ecs,
    aws_iam,
    aws_ec2,
    aws_lambda,
    aws_elasticloadbalancingv2 as elbv2,
    aws_codedeploy as codedeploy,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions,
    aws_s3 as s3,
    aws_cloudwatch,
    aws_logs
)

class FlaskPipelineStack(core.Stack):
    

    def __init__(self, scope: core.Construct, id: str, vpc:aws_ec2.Vpc, ecs_cluster=aws_ecs.Cluster,**kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ECS_APP_NAME="Flask-app",
        ECS_DEPLOYMENT_GROUP_NAME = "FlaskAppECSBlueGreen"
        ECS_DEPLOYMENT_CONFIG_NAME = "CodeDeployDefault.ECSAllAtOnce"
        ECS_TASKSET_TERMINATION_WAIT_TIME = 10
        ECS_TASK_FAMILY_NAME = "Flask-microservice"
        ECS_APP_NAME = "Flask-microservice"
        ECS_APP_LOG_GROUP_NAME = "/ecs/Flask-microservice"
        DUMMY_TASK_FAMILY_NAME = "sample-Nginx-microservice"
        DUMMY_APP_NAME = "sample-Nginx-microservice"
        DUMMY_APP_LOG_GROUP_NAME = "/ecs/sample-Nginx-microservice"
        DUMMY_CONTAINER_IMAGE = "smuralee/nginx"


        # =============================================================================
        # ECR and CodeCommit repositories for the Blue/ Green deployment
        # =============================================================================

        # ECR repository for the docker images
        FlaskecrRepo = aws_ecr.Repository(self, "FlaskRepo",
            image_scan_on_push=True
        )

        FlaskCodeCommitrepo = aws_codecommit.Repository(self, "FlaskRepository",
            repository_name=ECS_APP_NAME,
            description="Oussama Flask application"
        )

        # =============================================================================
        #   CODE BUILD and ECS TASK ROLES for the Blue/ Green deployment
        # =============================================================================

        # IAM role for the Code Build project
        FlaskcodeBuildServiceRole = aws_iam.Role(self, "FlaskcodeBuildServiceRole",
            assumed_by=aws_iam.ServicePrincipal('codebuild.amazonaws.com')
        )

        inlinePolicyForCodeBuild = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=[
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            resources=["*"]
        )

        FlaskcodeBuildServiceRole.add_to_policy(inlinePolicyForCodeBuild)

        # ECS task role
        FlaskecsTaskRole = aws_iam.Role(self, "FlaskecsTaskRole", 
            assumed_by=aws_iam.ServicePrincipal('ecs-tasks.amazonaws.com')
        )

        FlaskecsTaskRole.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"))

        # =============================================================================
        # CODE BUILD PROJECT for the Blue/ Green deployment
        # =============================================================================

        # Creating the code build project
        FlaskAppcodebuild = aws_codebuild.Project(self, "FlaskAppCodeBuild",
            role=FlaskcodeBuildServiceRole,
            environment=aws_codebuild.BuildEnvironment(
                build_image=aws_codebuild.LinuxBuildImage.STANDARD_4_0,
                compute_type=aws_codebuild.ComputeType.SMALL,
                privileged=True,
                environment_variables={
                    'REPOSITORY_URI':{
                        'value': FlaskecrRepo.repository_uri,
                        'type': aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT
                    },
                    'TASK_EXECUTION_ARN':{
                        'value': FlaskecsTaskRole.role_arn,
                        'type': aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT
                    },
                    'TASK_FAMILY': {
                        'value': ECS_TASK_FAMILY_NAME,
                        'type': aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT
                    }
                }
            ),
            source=aws_codebuild.Source.code_commit(repository=FlaskCodeCommitrepo)
        )

        # =============================================================================
        # CODE DEPLOY APPLICATION for the Blue/ Green deployment
        # =============================================================================

        # Creating the code deploy application
        FlaskcodeDeployApplication = codedeploy.EcsApplication(self, "FlaskAppCodeDeploy");

        # Creating the code deploy service role
        FlaskcodeDeployServiceRole = aws_iam.Role(self, "FlaskcodeDeployServiceRole",
            assumed_by=aws_iam.ServicePrincipal('codedeploy.amazonaws.com')
        )
        FlaskcodeDeployServiceRole.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeDeployRoleForECS"));


        # IAM role for custom lambda function
        FlaskcustomLambdaServiceRole = aws_iam.Role(self, "FlaskcodeDeployCustomLambda",
            assumed_by= aws_iam.ServicePrincipal('lambda.amazonaws.com')
        )

        inlinePolicyForLambda = aws_iam.PolicyStatement(
            effect= aws_iam.Effect.ALLOW,
            actions=[
                "iam:PassRole",
                "sts:AssumeRole",
                "codedeploy:List*",
                "codedeploy:Get*",
                "codedeploy:UpdateDeploymentGroup",
                "codedeploy:CreateDeploymentGroup",
                "codedeploy:DeleteDeploymentGroup"
            ],
            resources= ["*"]
        )

        FlaskcustomLambdaServiceRole.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        FlaskcustomLambdaServiceRole.add_to_policy(inlinePolicyForLambda);

        # Custom resource to create the deployment group
        createFlaskDeploymentGroupLambda = aws_lambda.Function(self, 'createFlaskDeploymentGroupLambda',
            code = aws_lambda.Code.from_asset("custom_resources"),
            runtime= aws_lambda.Runtime.PYTHON_3_8,
            handler= 'create_deployment_group.handler',
            role= FlaskcustomLambdaServiceRole,
            description= "Custom resource to create deployment group",
            memory_size= 128,
            timeout= core.Duration.seconds(60)
        )

        # =============================================================================
        # VPC, ECS Cluster, ELBs and Target groups for the Blue/ Green deployment
        # =============================================================================

        # Creating an application load balancer, listener and two target groups for  deployment
        Flaskalb = elbv2.ApplicationLoadBalancer(self, "Flaskalb",
            vpc= vpc,
            internet_facing=True
        )

        FlaskalbProdListener = Flaskalb.add_listener('FlaskalbProdListener',
            port=80,
        )

        FlaskalbTestListener = Flaskalb.add_listener('FlaskalbTestListener',
            port=8080,
        )

        FlaskalbProdListener.connections.allow_default_port_from_any_ipv4('Allow traffic from everywhere')
        FlaskalbTestListener.connections.allow_default_port_from_any_ipv4('Allow traffic from everywhere')
        # Target Group 1
        FlaskBlueGroup = elbv2.ApplicationTargetGroup(self, "FlaskBlueGroup",
            vpc=vpc,
            protocol=elbv2.ApplicationProtocol.HTTP,
            port=80,
            target_type=elbv2.TargetType.IP,
            health_check={
                "path": "/api/test",
                "timeout": core.Duration.seconds(10),
                "interval": core.Duration.seconds(15),
                "healthy_http_codes": "200,404"
            }
        )

        # elbv2.ApplicationListenerRule(self,
        #     id="FlaskAlbListenerRule", 
        #     path_pattern="/api/*", 
        #     priority=1, 
        #     listener=FlaskalbProdListener, 
        #     target_groups=[FlaskBlueGroup]
        # )

        # Target Group 2
        FlaskGreenGroup = elbv2.ApplicationTargetGroup(self, "FlaskGreenGroup",
            vpc=vpc,
            protocol=elbv2.ApplicationProtocol.HTTP,
            port=80,
            target_type=elbv2.TargetType.IP,
            health_check={
                "path": "/api/test",
                "timeout": core.Duration.seconds(10),
                "interval": core.Duration.seconds(15),
                "healthy_http_codes": "200,404"
            }
        )

        #TODO Delete this after using one load balancer for all microservices
        FlaskalbProdListener.add_fixed_response("DummyResponsePrd",
            status_code= "404"
        )

        FlaskalbTestListener.add_fixed_response("DummyResponseTest",
            status_code= "404"
            )
        # Registering the blue target group with the production listener of load balancer

        FlaskalbProdListener.add_target_groups("blueTarget",
            priority=1, 
            path_pattern = "/api/*",
            target_groups= [FlaskBlueGroup]
        )

        # Registering the green target group with the test listener of load balancer

        FlaskalbTestListener.add_target_groups("greenTarget",
            priority=1, 
            path_pattern = "/api/*",
            target_groups= [FlaskGreenGroup]
        )

       # ================================================================================================
        # CloudWatch Alarms for 4XX errors
        Flaskblue4xxMetric = aws_cloudwatch.Metric(
            namespace= 'AWS/ApplicationELB',
            metric_name= 'FlaskHTTPCode_Target_4XX_Count',
            dimensions={
                "TargetGroup":FlaskBlueGroup.target_group_full_name,
                "LoadBalancer":Flaskalb.load_balancer_full_name
            },
            statistic="sum",
            period=core.Duration.minutes(1)
        )

        FlaskblueGroupAlarm = aws_cloudwatch.Alarm(self, "Flaskblue4xxErrors",
            alarm_name= "FlaskBlue_4xx_Alarm",
            alarm_description= "CloudWatch Alarm for the 4xx errors of Blue target group",
            metric= Flaskblue4xxMetric,
            threshold= 1,
            evaluation_periods= 1
        )

        Flaskgreen4xxMetric = aws_cloudwatch.Metric(
            namespace= 'AWS/ApplicationELB',
            metric_name= 'FlaskHTTPCode_Target_4XX_Count',
            dimensions= {
                "TargetGroup":FlaskGreenGroup.target_group_full_name,
                "LoadBalancer":Flaskalb.load_balancer_full_name
            },
            statistic= "sum",
            period= core.Duration.minutes(1)
        )
        FlaskgreenGroupAlarm = aws_cloudwatch.Alarm(self, "Flaskgreen4xxErrors",
            alarm_name= "FlaskGreen_4xx_Alarm",
            alarm_description= "CloudWatch Alarm for the 4xx errors of Green target group",
            metric= Flaskgreen4xxMetric,
            threshold= 1,
            evaluation_periods= 1
        )

        # ================================================================================================
        # ECS task definition using ECR image
        # Will be used by the CODE DEPLOY for  deployment
        # ================================================================================================
        FlaskTaskDefinition = aws_ecs.FargateTaskDefinition(self, "FlaskappTaskDefn", 
            family= ECS_TASK_FAMILY_NAME,
            cpu= 256,
            memory_limit_mib= 1024,
            task_role= FlaskecsTaskRole,
            execution_role= FlaskecsTaskRole
        )

        FlaskcontainerDefinition = FlaskTaskDefinition.add_container("FlaskAppContainer",
            image= aws_ecs.ContainerImage.from_ecr_repository(FlaskecrRepo, "latest"),
            logging= aws_ecs.AwsLogDriver(
                log_group= aws_logs.LogGroup(self, "FlaskAppLogGroup",
                    log_group_name= ECS_APP_LOG_GROUP_NAME,
                    removal_policy= core.RemovalPolicy.DESTROY
                ),
                stream_prefix=ECS_APP_NAME
            ),
            docker_labels= {
                "name": ECS_APP_NAME
            }
        )

        port_mapping = aws_ecs.PortMapping(
            container_port=80,
            protocol=aws_ecs.Protocol.TCP
        )

        FlaskcontainerDefinition.add_port_mappings(port_mapping)

        # =============================================================================
        # ECS SERVICE for the Blue/ Green deployment
        # =============================================================================
        FlaskAppService = aws_ecs.FargateService(self, "FlaskAppService",
            cluster=ecs_cluster,
            task_definition= FlaskTaskDefinition,
            health_check_grace_period= core.Duration.seconds(10),
            desired_count= 3,
            deployment_controller= {
                "type": aws_ecs.DeploymentControllerType.CODE_DEPLOY
            },
            service_name= ECS_APP_NAME
        )

        FlaskAppService.connections.allow_from(Flaskalb, aws_ec2.Port.tcp(80))
        FlaskAppService.connections.allow_from(Flaskalb, aws_ec2.Port.tcp(8080))
        FlaskAppService.attach_to_application_target_group(FlaskBlueGroup)

        # =============================================================================
        # CODE DEPLOY - Deployment Group CUSTOM RESOURCE for the Application deployment
        # =============================================================================


        core.CustomResource(self, 'FlaskcustomEcsDeploymentGroup',
            service_token= createFlaskDeploymentGroupLambda.function_arn,
            properties= {
                "ApplicationName": FlaskcodeDeployApplication.application_name,
                "DeploymentGroupName": ECS_DEPLOYMENT_GROUP_NAME,
                "DeploymentConfigName": ECS_DEPLOYMENT_CONFIG_NAME,
                "ServiceRoleArn": FlaskcodeDeployServiceRole.role_arn,
                "BlueTargetGroup": FlaskBlueGroup.target_group_name,
                "GreenTargetGroup": FlaskGreenGroup.target_group_name,
                "ProdListenerArn": FlaskalbProdListener.listener_arn,
                "TestListenerArn": FlaskalbTestListener.listener_arn,
                "EcsClusterName": ecs_cluster.cluster_name,
                "EcsServiceName": FlaskAppService.service_name,
                "TerminationWaitTime": ECS_TASKSET_TERMINATION_WAIT_TIME,
                "BlueGroupAlarm": FlaskblueGroupAlarm.alarm_name,
                "GreenGroupAlarm": FlaskgreenGroupAlarm.alarm_name,
            }
        )

        FlaskecsDeploymentGroup = codedeploy.EcsDeploymentGroup.from_ecs_deployment_group_attributes(self, "FlaskecsDeploymentGroup",
            application= FlaskcodeDeployApplication,
            deployment_group_name= ECS_DEPLOYMENT_GROUP_NAME,
            deployment_config= codedeploy.EcsDeploymentConfig.from_ecs_deployment_config_name(self, "FlaskecsDeploymentConfig", ECS_DEPLOYMENT_CONFIG_NAME)
        )
        # =============================================================================
        # CODE PIPELINE for  ECS deployment
        # =============================================================================

        FlaskcodePipelineServiceRole = aws_iam.Role(self, "FlaskcodePipelineServiceRole", 
            assumed_by=aws_iam.ServicePrincipal('codepipeline.amazonaws.com')
        )

        inlinePolicyForCodePipeline = aws_iam.PolicyStatement(
            effect= aws_iam.Effect.ALLOW,
            actions= [
                "iam:PassRole",
                "sts:AssumeRole",
                "codecommit:Get*",
                "codecommit:List*",
                "codecommit:GitPull",
                "codecommit:UploadArchive",
                "codecommit:CancelUploadArchive",
                "codebuild:BatchGetBuilds",
                "codebuild:StartBuild",
                "codedeploy:CreateDeployment",
                "codedeploy:Get*",
                "codedeploy:RegisterApplicationRevision",
                "s3:Get*",
                "s3:List*",
                "s3:PutObject"
            ],
            resources= ["*"]
        )

        FlaskcodePipelineServiceRole.add_to_policy(inlinePolicyForCodePipeline);

        sourceArtifact = codepipeline.Artifact('sourceArtifact')
        buildArtifact = codepipeline.Artifact('buildArtifact')

        # S3 bucket for storing the code pipeline artifacts
        FlaskAppArtifactsBucket = s3.Bucket(self, "FlaskAppArtifactsBucket",
            encryption= s3.BucketEncryption.S3_MANAGED,
            block_public_access= s3.BlockPublicAccess.BLOCK_ALL
        )

        # S3 bucket policy for the code pipeline artifacts
        FlaskBucketdenyUnEncryptedObjectUploads = aws_iam.PolicyStatement(
            effect= aws_iam.Effect.DENY,
            actions= ["s3:PutObject"],
            principals= [aws_iam.AnyPrincipal()],
            resources= [FlaskAppArtifactsBucket.bucket_arn+"/*"],
            conditions={
                "StringNotEquals":{
                    "s3:x-amz-server-side-encryption": "aws:kms"
                }
            }
        )

        FlaskBucketdenyInsecureConnections = aws_iam.PolicyStatement(
            effect= aws_iam.Effect.DENY,
            actions= ["s3:*"],
            principals= [aws_iam.AnyPrincipal()],
            resources= [FlaskAppArtifactsBucket.bucket_arn+"/*"],
            conditions= {
                "Bool":{
                    "aws:SecureTransport": "false"
                }
            }
        )

        FlaskAppArtifactsBucket.add_to_resource_policy(FlaskBucketdenyUnEncryptedObjectUploads)
        FlaskAppArtifactsBucket.add_to_resource_policy(FlaskBucketdenyInsecureConnections)

        # Code Pipeline - CloudWatch trigger event is created by CDK
        codepipeline.Pipeline(self, "FlaskECSPipeline", 
            role= FlaskcodePipelineServiceRole,
            artifact_bucket= FlaskAppArtifactsBucket,
            stages=[
                codepipeline.StageProps(
                    stage_name='Source',
                    actions= [
                        aws_codepipeline_actions.CodeCommitSourceAction(
                            action_name= 'Source',
                            repository= FlaskCodeCommitrepo,
                            output= sourceArtifact,
                        )
                    ]
                ),
                codepipeline.StageProps(
                    stage_name= 'Build',
                    actions= [
                        aws_codepipeline_actions.CodeBuildAction(
                            action_name= 'Build',
                            project= FlaskAppcodebuild,
                            input= sourceArtifact,
                            outputs= [buildArtifact]
                        )
                    ]
                ),
                codepipeline.StageProps(
                    stage_name= 'Deploy',
                    actions= [
                        aws_codepipeline_actions.CodeDeployEcsDeployAction(
                            action_name= 'Deploy',
                            deployment_group= FlaskecsDeploymentGroup,
                            app_spec_template_input= buildArtifact,
                            task_definition_template_input= buildArtifact,
                        )
                    ]
                )
            ]
        )

        # =============================================================================
        # Export the outputs
        # =============================================================================
        core.CfnOutput(self, "FlaskECSCodeRepo", 
            description= "Flask code commit repository",
            export_name= "FlaskAppRepo",
            value= FlaskCodeCommitrepo.repository_clone_url_http
        )

        core.CfnOutput(self, "FlaskLBDns", 
            description= "Load balancer DNS",
            export_name= "FlaskLBDns",
            value= Flaskalb.load_balancer_dns_name
        )