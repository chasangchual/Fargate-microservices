from aws_cdk import(
    aws_s3 as s3,
    aws_cloudfront as cdn,
    aws_ssm as ssm,
    aws_route53 as r53,
    aws_route53_targets as r53targets,
    aws_elasticloadbalancingv2 as elbv2,
    core
)

class CDNStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, s3bucket, acmcert, hostedzone,alb=elbv2.ApplicationLoadBalancer, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        prj_name    = self.node.try_get_context("project_name")
        env_name    = self.node.try_get_context("env")
        domain_name = self.node.try_get_context("domain_name")

        bucketName = s3.Bucket.from_bucket_name(self, 's3bucket',s3bucket )

        path_patterns = ["/static/*", "/templates/*"]

        self.cdn_id = cdn.CloudFrontWebDistribution(self,'webhosting-cdn',
            origin_configs=[
                cdn.SourceConfiguration(
                 #   origin_path="/",
                    s3_origin_source=cdn.S3OriginConfig(
                        s3_bucket_source=bucketName,
                        origin_access_identity=cdn.OriginAccessIdentity(self,'webhosting-origin')
                    ),
                    behaviors=[
                        cdn.Behavior(
                            path_pattern=path_pattern,
                            allowed_methods= cdn.CloudFrontAllowedMethods.ALL,
                            cached_methods= cdn.CloudFrontAllowedCachedMethods.GET_HEAD,
                        )
                        for path_pattern in path_patterns
                    ],
                ),
                cdn.SourceConfiguration(
                    custom_origin_source=cdn.CustomOriginConfig(
                        domain_name=alb.load_balancer_dns_name,
                        origin_protocol_policy= cdn.OriginProtocolPolicy.MATCH_VIEWER
                ),
                    behaviors = [ 
                        cdn.Behavior(
                            is_default_behavior=True,
                            allowed_methods= cdn.CloudFrontAllowedMethods.ALL,
                            forwarded_values= {
                                "query_string":True,
                                "cookies": {"forward": "all"},
                                "headers": ['*']
                            },
                        )
                    ]   
                )
            ],

            error_configurations=[cdn.CfnDistribution.CustomErrorResponseProperty(
                error_code=400,
                response_code=200,
                response_page_path="/"

            ),
                cdn.CfnDistribution.CustomErrorResponseProperty(
                    error_code=403,
                    response_code=200,
                    response_page_path="/"
                ),
                cdn.CfnDistribution.CustomErrorResponseProperty(
                    error_code=404,
                    response_code=200,
                    response_page_path="/"
                )
            ],
            alias_configuration=cdn.AliasConfiguration(
                acm_cert_ref=acmcert.certificate_arn,
                names=[env_name+'.'+domain_name]
            )
        )


        r53.ARecord(self, 'dev-record',
            zone=hostedzone,
            target=r53.RecordTarget.from_alias(alias_target=r53targets.CloudFrontTarget(self.cdn_id)),
            #target=r53.RecordTarget.from_alias(alias_target="d1w8o2vctuxdpo.cloudfront.net"),
            record_name='dev'
        )


        ssm.StringParameter(self,'cdn-dist-id',
            parameter_name='/'+env_name+'/app-distribution-id',
            string_value=self.cdn_id.distribution_id
        )

        ssm.StringParameter(self,'cdn-url',
            parameter_name='/'+env_name+'/app-cdn-url',
            string_value='https://'+self.cdn_id.domain_name
        )
