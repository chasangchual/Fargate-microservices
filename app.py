#!/usr/bin/env python3

from aws_cdk import core
from stacks.vpc_stack import VPCStack



app            = core.App()
vpc_stack      = VPCStack(app, 'vpc')



app.synth()
