#!/usr/bin/env python3

from aws_cdk import core
from stacks.vpc_stack import VPCStack
from stacks.ecs_stack import ECSStack
from stacks.bluegreen_stack import BlueGreen
from stacks.flask_pipeline_stack import FlaskPipelineStack
from stacks.alb_stack import AlbStack
from stacks.s3_stack import S3Stack
from stacks.dns_stack import DNSStack
from stacks.acm_stack import ACMStack
from stacks.cdn_stack import CDNStack


app                     = core.App()
vpc_stack               = VPCStack(app, 'vpc-stack')
ecs_stack               = ECSStack(app, 'ecs-stack', vpc=vpc_stack.vpc)
alb_stack               = AlbStack(app,'alb-stack', vpc=vpc_stack.vpc)
s3_stack                = S3Stack(app, 's3-stack')
dns_stack               = DNSStack(app,'dns-stack')
acm_stack               = ACMStack(app, 'acm-stack')
cdn_stack               = CDNStack(app, 'cdn-stack',s3bucket=core.Fn.import_value('FlaskFrontendBucket'),
                                            acmcert=acm_stack.cert_manager,
                                            hostedzone=dns_stack.hosted_zone,
                                            alb=alb_stack.alb,
                                            )
bluegreen_stack         = BlueGreen(app, 'bluegreen-stack', vpc=vpc_stack.vpc, 
                                            ecs_cluster=ecs_stack.ecs_cluster,
                                            alb=alb_stack.alb, 
                                            albTestListener=alb_stack.albTestListener,   
                                            albProdListener=alb_stack.albProdListener,
                                            blueGroup=alb_stack.blueGroup,
                                            greenGroup=alb_stack.greenGroup,
                                            )
flask_pipeline_stack    = FlaskPipelineStack(app, 'flask-pipeline-stack',vpc=vpc_stack.vpc, 
                                            ecs_cluster=ecs_stack.ecs_cluster, 
                                            alb=alb_stack.alb, 
                                            albTestListener=alb_stack.albTestListener,   
                                            albProdListener=alb_stack.albProdListener,
                                            FlaskBlueGroup=alb_stack.FlaskBlueGroup,
                                            FlaskGreenGroup=alb_stack.FlaskGreenGroup,
                                            )


app.synth()
