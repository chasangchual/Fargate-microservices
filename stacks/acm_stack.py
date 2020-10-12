from aws_cdk import (
    aws_certificatemanager as acm,
    aws_route53 as r53,
    aws_iam as iam,
    aws_cloudfront as cdn,
    aws_ssm as ssm,
    core
) 

class ACMStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str,  **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        prj_name = self.node.try_get_context("project_name")
        env_name = self.node.try_get_context("env")
        domain_name = self.node.try_get_context("domain_name")

        zone_id = ssm.StringParameter.from_string_parameter_name(self, 'zone-id-ssm', string_parameter_name='/'+env_name+'/zone-id')

        dns_zone = r53.HostedZone.from_hosted_zone_attributes(self, 'hosted-zone',
            hosted_zone_id=zone_id.string_value,
            zone_name=domain_name
        )

        self.cert_manager = acm.DnsValidatedCertificate(self, 'acm-id',
            hosted_zone=dns_zone,
            domain_name=domain_name,
            subject_alternative_names=['*.'+domain_name],
            region= 'us-east-1'
        )

        self.cert_manager_eu = acm.DnsValidatedCertificate(self, 'acm-eu-central',
            hosted_zone=dns_zone,
            domain_name=domain_name,
            subject_alternative_names=['*.'+domain_name],
            region= 'eu-central-1'
        )
        