from aws_cdk import(
    aws_route53 as r53,
    aws_iam as iam,
    aws_cloudfront as cdn,
    aws_ssm as ssm,
    core
)

class DNSStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        prj_name    = self.node.try_get_context("project_name")
        env_name    = self.node.try_get_context("env")
        domain_name = self.node.try_get_context("domain_name")

        self.hosted_zone =r53.HostedZone(self, 'hosted-zone',
            zone_name= domain_name
        )

        ssm.StringParameter(self,'zone-id',
            parameter_name='/'+env_name+'/zone-id',
            string_value=self.hosted_zone.hosted_zone_id
        )