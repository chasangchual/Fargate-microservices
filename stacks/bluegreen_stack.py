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

class BlueGreen(core.Stack):
    

    def __init__(self, scope: core.Construct, id: str, vpc:aws_ec2.Vpc, ecs_cluster=aws_ecs.Cluster, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ECS_APP_NAME="Nginx-app",
        ECS_DEPLOYMENT_GROUP_NAME = "NginxAppECSBlueGreen"
        ECS_DEPLOYMENT_CONFIG_NAME = "CodeDeployDefault.ECSLinear10PercentEvery1Minutes"
        ECS_TASKSET_TERMINATION_WAIT_TIME = 10
        ECS_TASK_FAMILY_NAME = "Nginx-microservice"
        ECS_APP_NAME = "Nginx-microservice"
        ECS_APP_LOG_GROUP_NAME = "/ecs/Nginx-microservice"
        DUMMY_TASK_FAMILY_NAME = "sample-Nginx-microservice"
        DUMMY_APP_NAME = "sample-Nginx-microservice"
        DUMMY_APP_LOG_GROUP_NAME = "/ecs/sample-Nginx-microservice"
        DUMMY_CONTAINER_IMAGE = "smuralee/nginx"


        # =============================================================================
        # ECR and CodeCommit repositories for the Blue/ Green deployment
        # =============================================================================

        # ECR repository for the docker images
        NginxecrRepo = aws_ecr.Repository(self, "NginxRepo",
            image_scan_on_push=True
        )

        NginxCodeCommitrepo = aws_codecommit.Repository(self, "NginxRepository",
            repository_name=ECS_APP_NAME,
            description="Oussama application hosted on NGINX"
        )

        # =============================================================================
        #   CODE BUILD and ECS TASK ROLES for the Blue/ Green deployment
        # =============================================================================

        # IAM role for the Code Build project
        codeBuildServiceRole = aws_iam.Role(self, "codeBuildServiceRole",
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

        codeBuildServiceRole.add_to_policy(inlinePolicyForCodeBuild)

        # ECS task role
        ecsTaskRole = aws_iam.Role(self, "ecsTaskRoleForWorkshop", 
            assumed_by=aws_iam.ServicePrincipal('ecs-tasks.amazonaws.com')
        )

        ecsTaskRole.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"))

        # =============================================================================
        # CODE DEPLOY APPLICATION for the Blue/ Green deployment
        # =============================================================================

        # Creating the code deploy application
        codeDeployApplication = codedeploy.EcsApplication(self, "NginxAppCodeDeploy");

        # Creating the code deploy service role
        codeDeployServiceRole = aws_iam.Role(self, "codeDeployServiceRole",
            assumed_by=aws_iam.ServicePrincipal('codedeploy.amazonaws.com')
        )
        codeDeployServiceRole.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeDeployRoleForECS"));

        # IAM role for custom lambda function
        customLambdaServiceRole = aws_iam.Role(self, "codeDeployCustomLambda",
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

        customLambdaServiceRole.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        customLambdaServiceRole.add_to_policy(inlinePolicyForLambda);

        # Custom resource to create the deployment group
        createDeploymentGroupLambda = aws_lambda.Function(self, 'createDeploymentGroupLambda',
            code = aws_lambda.Code.from_asset("custom_resources"),
            runtime= aws_lambda.Runtime.PYTHON_3_8,
            handler= 'create_deployment_group.handler',
            role= customLambdaServiceRole,
            description= "Custom resource to create deployment group",
            memory_size= 128,
            timeout= core.Duration.seconds(60)
        )


        # =============================================================================
        # VPC, ECS Cluster, ELBs and Target groups for the Blue/ Green deployment
        # =============================================================================

        # Creating an application load balancer, listener and two target groups for Blue/Green deployment
        alb = elbv2.ApplicationLoadBalancer(self, "alb",
            vpc= vpc,
            internet_facing=True
        )
        
        albProdListener = alb.add_listener('albProdListener',
            port=80
        )
        
        albTestListener = alb.add_listener('albTestListener',
            port=8080
        )

        albProdListener.connections.allow_default_port_from_any_ipv4('Allow traffic from everywhere')
        albTestListener.connections.allow_default_port_from_any_ipv4('Allow traffic from everywhere')

        # Target group 1
        blueGroup = elbv2.ApplicationTargetGroup(self, "blueGroup",
            vpc=vpc,
            protocol=elbv2.ApplicationProtocol.HTTP,
            port=80,
            target_type=elbv2.TargetType.IP,
            health_check={
                "path": "/",
                "timeout": core.Duration.seconds(10),
                "interval": core.Duration.seconds(15),
                "healthy_http_codes": "200,404"
            }
        )

        # Target group 2
        greenGroup = elbv2.ApplicationTargetGroup(self, "greenGroup",
            vpc=vpc,
            protocol=elbv2.ApplicationProtocol.HTTP,
            port=80,
            target_type=elbv2.TargetType.IP,
            health_check={
                "path": "/",
                "timeout": core.Duration.seconds(10),
                "interval": core.Duration.seconds(15),
                "healthy_http_codes": "200,404"
            }
        )

        # Registering the blue target group with the production listener of load balancer
        albProdListener.add_target_groups("blueTarget",
            target_groups= [blueGroup]
        )


        # Registering the green target group with the test listener of load balancer
        albTestListener.add_target_groups("greenTarget",
            target_groups= [greenGroup]
        )

        # ================================================================================================
        # CloudWatch Alarms for 4XX errors
        blue4xxMetric = aws_cloudwatch.Metric(
            namespace= 'AWS/ApplicationELB',
            metric_name= 'HTTPCode_Target_4XX_Count',
            dimensions={
                "TargetGroup":blueGroup.target_group_full_name,
                "LoadBalancer":alb.load_balancer_full_name
            },
            statistic="sum",
            period=core.Duration.minutes(1)
        )

        blueGroupAlarm = aws_cloudwatch.Alarm(self, "blue4xxErrors",
            alarm_name= "Blue_4xx_Alarm",
            alarm_description= "CloudWatch Alarm for the 4xx errors of Blue target group",
            metric= blue4xxMetric,
            threshold= 1,
            evaluation_periods= 1
        )

        green4xxMetric = aws_cloudwatch.Metric(
            namespace= 'AWS/ApplicationELB',
            metric_name= 'HTTPCode_Target_4XX_Count',
            dimensions= {
                "TargetGroup":greenGroup.target_group_full_name,
                "LoadBalancer":alb.load_balancer_full_name
            },
            statistic= "sum",
            period= core.Duration.minutes(1)
        )
        greenGroupAlarm = aws_cloudwatch.Alarm(self, "green4xxErrors",
            alarm_name= "Green_4xx_Alarm",
            alarm_description= "CloudWatch Alarm for the 4xx errors of Green target group",
            metric= green4xxMetric,
            threshold= 1,
            evaluation_periods= 1
        )

        # ================================================================================================
        # DUMMY TASK DEFINITION for the initial service creation
        # This is required for the service being made available to create the CodeDeploy Deployment Group
        # ================================================================================================
        sampleTaskDefinition = aws_ecs.FargateTaskDefinition(self, "sampleTaskDefn", 
            family= DUMMY_TASK_FAMILY_NAME,
            cpu= 256,
            memory_limit_mib= 1024,
            task_role= ecsTaskRole,
            execution_role= ecsTaskRole
        )

        sampleContainerDefn = sampleTaskDefinition.add_container("sampleAppContainer",
            image=aws_ecs.ContainerImage.from_registry(DUMMY_CONTAINER_IMAGE),
            logging=aws_ecs.AwsLogDriver(
                log_group=aws_logs.LogGroup(self, "sampleAppLogGroup", 
                    log_group_name= DUMMY_APP_LOG_GROUP_NAME,
                    removal_policy= core.RemovalPolicy.DESTROY
                ),
                stream_prefix=DUMMY_APP_NAME
            ),
            docker_labels= {
                "name": DUMMY_APP_NAME
            }
        )

        port_mapping = aws_ecs.PortMapping(
            container_port=80,
            protocol=aws_ecs.Protocol.TCP
        )

        sampleContainerDefn.add_port_mappings(port_mapping)

        # ================================================================================================
        # ECS task definition using ECR image
        # Will be used by the CODE DEPLOY for Blue/Green deployment
        # ================================================================================================
        NginxTaskDefinition = aws_ecs.FargateTaskDefinition(self, "appTaskDefn", 
            family= ECS_TASK_FAMILY_NAME,
            cpu= 256,
            memory_limit_mib= 1024,
            task_role= ecsTaskRole,
            execution_role= ecsTaskRole
        )

        NginxcontainerDefinition = NginxTaskDefinition.add_container("NginxAppContainer",
            image= aws_ecs.ContainerImage.from_ecr_repository(NginxecrRepo, "latest"),
            logging= aws_ecs.AwsLogDriver(
                log_group= aws_logs.LogGroup(self, "NginxAppLogGroup",
                    log_group_name= ECS_APP_LOG_GROUP_NAME,
                    removal_policy= core.RemovalPolicy.DESTROY
                ),
                stream_prefix=ECS_APP_NAME
            ),
            docker_labels= {
                "name": ECS_APP_NAME
            }
        )
        NginxcontainerDefinition.add_port_mappings(port_mapping)

        # =============================================================================
        # ECS SERVICE for the Blue/ Green deployment
        # =============================================================================
        NginxAppService = aws_ecs.FargateService(self, "NginxAppService",
            cluster=ecs_cluster,
            task_definition= NginxTaskDefinition,
            health_check_grace_period= core.Duration.seconds(10),
            desired_count= 3,
            deployment_controller= {
                "type": aws_ecs.DeploymentControllerType.CODE_DEPLOY
            },
            service_name= ECS_APP_NAME
        )

        NginxAppService.connections.allow_from(alb, aws_ec2.Port.tcp(80))
        NginxAppService.connections.allow_from(alb, aws_ec2.Port.tcp(8080))
        NginxAppService.attach_to_application_target_group(blueGroup);

        # =============================================================================
        # CODE DEPLOY - Deployment Group CUSTOM RESOURCE for the Blue/ Green deployment
        # =============================================================================


        core.CustomResource(self, 'customEcsDeploymentGroup',
            service_token= createDeploymentGroupLambda.function_arn,
            properties= {
                "ApplicationName": codeDeployApplication.application_name,
                "DeploymentGroupName": ECS_DEPLOYMENT_GROUP_NAME,
                "DeploymentConfigName": ECS_DEPLOYMENT_CONFIG_NAME,
                "ServiceRoleArn": codeDeployServiceRole.role_arn,
                "BlueTargetGroup": blueGroup.target_group_name,
                "GreenTargetGroup": greenGroup.target_group_name,
                "ProdListenerArn": albProdListener.listener_arn,
                "TestListenerArn": albTestListener.listener_arn,
                "EcsClusterName": ecs_cluster.cluster_name,
                "EcsServiceName": NginxAppService.service_name,
                "TerminationWaitTime": ECS_TASKSET_TERMINATION_WAIT_TIME,
                "BlueGroupAlarm": blueGroupAlarm.alarm_name,
                "GreenGroupAlarm": greenGroupAlarm.alarm_name,
            }
        )

        ecsDeploymentGroup = codedeploy.EcsDeploymentGroup.from_ecs_deployment_group_attributes(self, "ecsDeploymentGroup",
            application= codeDeployApplication,
            deployment_group_name= ECS_DEPLOYMENT_GROUP_NAME,
            deployment_config= codedeploy.EcsDeploymentConfig.from_ecs_deployment_config_name(self, "ecsDeploymentConfig", ECS_DEPLOYMENT_CONFIG_NAME)
        )


        # =============================================================================
        # CODE BUILD PROJECT for the Blue/ Green deployment
        # =============================================================================

        # Creating the code build project
        NginxAppcodebuild = aws_codebuild.Project(self, "NginxAppCodeBuild",
            role=codeBuildServiceRole,
            environment=aws_codebuild.BuildEnvironment(
                build_image=aws_codebuild.LinuxBuildImage.STANDARD_4_0,
                compute_type=aws_codebuild.ComputeType.SMALL,
                privileged=True,
                environment_variables={
                    'REPOSITORY_URI':{
                        'value': NginxecrRepo.repository_uri,
                        'type': aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT
                    },
                    'TASK_EXECUTION_ARN':{
                        'value': ecsTaskRole.role_arn,
                        'type': aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT
                    },
                    'TASK_FAMILY': {
                        'value': ECS_TASK_FAMILY_NAME,
                        'type': aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT
                    }
                }
            ),
            source=aws_codebuild.Source.code_commit(repository=NginxCodeCommitrepo)
        )


        # =============================================================================
        # CODE PIPELINE for Blue/Green ECS deployment
        # =============================================================================

        codePipelineServiceRole = aws_iam.Role(self, "codePipelineServiceRole", 
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

        codePipelineServiceRole.add_to_policy(inlinePolicyForCodePipeline);

        sourceArtifact = codepipeline.Artifact('sourceArtifact');
        buildArtifact = codepipeline.Artifact('buildArtifact');

        # S3 bucket for storing the code pipeline artifacts
        NginxAppArtifactsBucket = s3.Bucket(self, "NginxAppArtifactsBucket",
            encryption= s3.BucketEncryption.S3_MANAGED,
            block_public_access= s3.BlockPublicAccess.BLOCK_ALL
        )

        # S3 bucket policy for the code pipeline artifacts
        denyUnEncryptedObjectUploads = aws_iam.PolicyStatement(
            effect= aws_iam.Effect.DENY,
            actions= ["s3:PutObject"],
            principals= [aws_iam.AnyPrincipal()],
            resources= [NginxAppArtifactsBucket.bucket_arn.join("/*")],
            conditions={
                "StringNotEquals":{
                    "s3:x-amz-server-side-encryption": "aws:kms"
                }
            }
        )

        denyInsecureConnections = aws_iam.PolicyStatement(
            effect= aws_iam.Effect.DENY,
            actions= ["s3:*"],
            principals= [aws_iam.AnyPrincipal()],
            resources= [NginxAppArtifactsBucket.bucket_arn.join("/*")],
            conditions= {
                "Bool": {
                    "aws:SecureTransport": "false"
                }
            }
        )

        NginxAppArtifactsBucket.add_to_resource_policy(denyUnEncryptedObjectUploads)
        NginxAppArtifactsBucket.add_to_resource_policy(denyInsecureConnections)

        # Code Pipeline - CloudWatch trigger event is created by CDK
        codepipeline.Pipeline(self, "ecsBlueGreen", 
            role= codePipelineServiceRole,
            artifact_bucket= NginxAppArtifactsBucket,
            stages=[
                codepipeline.StageProps(
                    stage_name='Source',
                    actions= [
                        aws_codepipeline_actions.CodeCommitSourceAction(
                            action_name= 'Source',
                            repository= NginxCodeCommitrepo,
                            output= sourceArtifact,
                        )
                    ]
                ),
                codepipeline.StageProps(
                    stage_name= 'Build',
                    actions= [
                        aws_codepipeline_actions.CodeBuildAction(
                            action_name= 'Build',
                            project= NginxAppcodebuild,
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
                            deployment_group= ecsDeploymentGroup,
                            app_spec_template_input= buildArtifact,
                            task_definition_template_input= buildArtifact,
                        )
                    ]
                )
            ]
        )
