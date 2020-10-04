from aws_cdk import (
    aws_ec2,
    aws_ecs,
    core,
    aws_iam,
)


class ECSStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str,vpc:aws_ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # ECS Cluster
        # https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_ecs.README.html#clusters
        self.ecs_cluster = aws_ecs.Cluster(
            self, "ECSCluster",
            vpc=vpc,
            cluster_name="Fargate-microservices"
        )

        # ECS Enable Cloud map
        self.ecs_cluster.add_default_cloud_map_namespace(
            name="service",
        )
        
        # ECS adding capacity
        self.asg = self.ecs_cluster.add_capacity(
           "ECSEC2Capacity",
           instance_type=aws_ec2.InstanceType(instance_type_identifier='t3.small'),
           min_capacity=0,
           max_capacity=10
        )
        
        core.CfnOutput(self, "EC2AutoScalingGroupName", value=self.asg.auto_scaling_group_name, export_name="EC2ASGName")
        
        # Namespace details as CFN output
        self.namespace_outputs = {
            'ARN': self.ecs_cluster.default_cloud_map_namespace.private_dns_namespace_arn,
            'NAME': self.ecs_cluster.default_cloud_map_namespace.private_dns_namespace_name,
            'ID': self.ecs_cluster.default_cloud_map_namespace.private_dns_namespace_id,
        }
        
        # Cluster Attributes
        self.cluster_outputs = {
            'NAME': self.ecs_cluster.cluster_name,
            'SECGRPS': str(self.ecs_cluster.connections.security_groups)
        }
        
        # When enabling EC2, we need the security groups "registered" to the cluster for imports in other service stacks
        if self.ecs_cluster.connections.security_groups:
            self.cluster_outputs['SECGRPS'] = str([x.security_group_id for x in self.ecs_cluster.connections.security_groups][0])
        
        
        # Allow inbound 80 from ALB to Frontend Service

        self.services_80_sec_group = aws_ec2.SecurityGroup(
            self, "FrontendToBackendSecurityGroup",
            allow_all_outbound=True,
            description="Security group to allow inbound 80 from ALB to Frontend Service",
            vpc=vpc
        )

        self.sec_grp_ingress_self_80 = aws_ec2.CfnSecurityGroupIngress(
            self, "InboundSecGrp3000",
            ip_protocol='TCP',
            source_security_group_id=self.services_80_sec_group.security_group_id,
            from_port=80,
            to_port=80,
            group_id=self.services_80_sec_group.security_group_id
        )
     
        # All Outputs required for other stacks to build
        core.CfnOutput(self, "NSArn", value=self.namespace_outputs['ARN'], export_name="NSARN")
        core.CfnOutput(self, "NSName", value=self.namespace_outputs['NAME'], export_name="NSNAME")
        core.CfnOutput(self, "NSId", value=self.namespace_outputs['ID'], export_name="NSID")
        core.CfnOutput(self, "FE2BESecGrp", value=self.services_80_sec_group.security_group_id, export_name="SecGrpId")
        core.CfnOutput(self, "ECSClusterName", value=self.cluster_outputs['NAME'], export_name="ECSClusterName")
        core.CfnOutput(self, "ECSClusterSecGrp", value=self.cluster_outputs['SECGRPS'], export_name="ECSSecGrpList")
        core.CfnOutput(self, "ServicesSecGrp", value=self.services_80_sec_group.security_group_id, export_name="ServicesSecGrp")