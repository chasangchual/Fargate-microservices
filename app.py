#!/usr/bin/env python3

from aws_cdk import core
from stacks.vpc_stack import VPCStack
from stacks.ecs_stack import ECSStack



app            = core.App()
vpc_stack      = VPCStack(app, 'vpc-stack')
ecs_stack      = ECSStack(app, 'ecs-stack', vpc=vpc_stack.vpc)



app.synth()
