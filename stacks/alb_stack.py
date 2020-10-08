from aws_cdk import (
    core,
    aws_ec2,
    aws_elasticloadbalancingv2 as elbv2,
)

class AlbStack(core.Stack):
    

    def __init__(self, scope: core.Construct, id: str, vpc:aws_ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

      # =============================================================================
        # VPC, ECS Cluster, ELBs and Target groups for the Blue/ Green deployment - Nginx
        # =============================================================================

        # Creating an application load balancer, listener and two target groups for Blue/Green deployment
        self.alb = elbv2.ApplicationLoadBalancer(self, "alb",
            vpc= vpc,
            internet_facing=True
        )
        
        self.albProdListener = self.alb.add_listener('albProdListener',
            port=80
        )
        
        self.albTestListener = self.alb.add_listener('albTestListener',
            port=8080
        )

        self.albProdListener.connections.allow_default_port_from_any_ipv4('Allow traffic from everywhere')
        self.albTestListener.connections.allow_default_port_from_any_ipv4('Allow traffic from everywhere')

        # Target group 1
        self.blueGroup = elbv2.ApplicationTargetGroup(self, "blueGroup",
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
        self.greenGroup = elbv2.ApplicationTargetGroup(self, "greenGroup",
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
        self.albProdListener.add_target_groups("blueTarget",
            target_groups= [blueGroup]
        )


        # Registering the green target group with the test listener of load balancer
        self.albTestListener.add_target_groups("greenTarget",
            target_groups= [greenGroup]
        )


       # =============================================================================
        # VPC, ECS Cluster, ELBs and Target groups for the Blue/ Green deployment - Flask
        # =============================================================================

        # Target Group 1
        self.FlaskBlueGroup = elbv2.ApplicationTargetGroup(self, "FlaskBlueGroup",
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

        # Target Group 2
        self.FlaskGreenGroup = elbv2.ApplicationTargetGroup(self, "FlaskGreenGroup",
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

        self.albProdListener.add_target_groups("FlaskblueTarget",
            priority=1, 
            path_pattern = "/api/*",
            target_groups= [FlaskBlueGroup]
        )

        # Registering the green target group with the test listener of load balancer

        self.albTestListener.add_target_groups("FlaskgreenTarget",
            priority=1, 
            path_pattern = "/api/*",
            target_groups= [FlaskGreenGroup]
        )
