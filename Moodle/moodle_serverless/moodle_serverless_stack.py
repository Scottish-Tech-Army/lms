from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_ecs as ecs, 
    aws_ecs_patterns as ecs_patterns, 
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_efs as efs,
    aws_iam as iam,
    aws_wafv2 as waf,
    aws_certificatemanager as cert_man,
    aws_route53 as rt53,
    #aws_lambda as lambda_,
    #aws_apigateway as apigateway,
    #aws_s3 as s3,
    #aws_lambda_event_sources as event_sources,
    aws_secretsmanager as secretsmanager,
    CfnOutput as CfnOutput,
    #aws_elasticloadbalancingv2 as elbv2
)
from constructs import Construct

class MoodleServerlessStackV2(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ## VPC
        vpc = ec2.Vpc(self, "Vpc", 
            max_azs=2,   # default is all AZs in region = 3
            # nat_gateways=1
            )

        ## RDS DATABASE - mysql
        ## https://aws.amazon.com/rds/instance-types/
        ## https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/DatabaseInstance.html
        data_base = rds.DatabaseInstance(self, "moodle-db",
            vpc=vpc,
            engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_0_31),
            instance_type=ec2.InstanceType('t4g.micro'), #https://aws.amazon.com/rds/mysql/pricing/?pg=pr&loc=2
            allocated_storage=5, 
            max_allocated_storage=20, #GiB
            database_name="moodledb",
            credentials=rds.Credentials.from_generated_secret("dbadmin", 
                exclude_characters='(" %+~`#$&*()|[]}{:;<>?!\'/^-,@_=\\'), # generate secret password for dbuser
            removal_policy=RemovalPolicy.DESTROY      # dev
            )

        # EFS elastic file system
        file_system = efs.FileSystem(self, "MoodleEfsFileSystem",
            vpc=vpc,
            lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,  # files are not transitioned to infrequent access (IA) storage by default
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,  # default
            out_of_infrequent_access_policy=efs.OutOfInfrequentAccessPolicy.AFTER_1_ACCESS,
            removal_policy=RemovalPolicy.DESTROY # dev
            )

        ## EFS access point
        access_point = efs.AccessPoint(self, "MoodleEfsAccessPoint",
            file_system=file_system,
            path="/",
            create_acl=efs.Acl(
                owner_uid="0",
                owner_gid="0",
                permissions="755"
                ),
            posix_user=efs.PosixUser(
                uid="0",
                gid="0"
                )
            )

        ## Variables to pass to ECS task as environment variables
        endpointaddress = data_base.db_instance_endpoint_address
        endpointport = data_base.db_instance_endpoint_port
        
        ## Variables to pass to task as secrets
        dbpassword = ecs.Secret.from_secrets_manager(
            data_base.secret, field="password") # secret containing the password auto generated by ...from_generated_secret("moodle")
        moodlepassword = secretsmanager.Secret(self, "Moodlepassword")

        ## Task image options for Fargate Task, references bitmani/moodle docker hub image,
        ## defines the task to impliment the containers
        task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
            image=ecs.ContainerImage.from_registry("bitnami/moodle"),
            container_name="MoodleContainer",
            container_port=8080,
# https://github.com/bitnami/containers/blob/main/bitnami/moodle/README.md#user-and-site-configuration
            environment={
                'MOODLE_DATABASE_TYPE': 'mysqli',
                'MOODLE_DATABASE_HOST': endpointaddress,
                'MOODLE_DATABASE_PORT_NUMBER': endpointport,
                'MOODLE_DATABASE_NAME': "moodledb",
                'MOODLE_DATABASE_USER': "dbadmin",
                'MOODLE_USERNAME': 'moodleadmin',
                #'MOODLE_PASSWORD': 'nmoodle',
                #'MOODLE_EMAIL': 'hello@example.com',
                'MOODLE_SITE_NAME': 'Scottish Tech Army',
                'MOODLE_SKIP_BOOTSTRAP': 'no',
                'MOODLE_SKIP_INSTALL': 'no',
                'BITNAMI_DEBUG': 'true',
                'PHP_UPLOAD_MAX_FILESIZE': '500M'},  # https://github.com/Scottish-Tech-Army/lms/issues/3
            secrets={"MOODLE_DATABASE_PASSWORD": dbpassword,
                    "MOODLE_PASSWORD": ecs.Secret.from_secrets_manager(moodlepassword)}
            )
        
        ## ECS container cluster for Moodle containers
        cluster = ecs.Cluster(self, "Moodle-Cluster", vpc=vpc)
        # ARN for certifcate from Certificate Manager
        certificate_arn = "arn:aws:acm:eu-west-2:131458236732:certificate/34bf02e0-4845-4e79-8036-9fb6dd0a8c4c"

        ## Fargate Service for container cluster with auto load balancer
        application = ecs_patterns.ApplicationLoadBalancedFargateService(self, 
            "moodleFargateService",
            cluster=cluster,            # Required
            #domain_name='',
            domain_zone=rt53.HostedZone.from_lookup(self, "TwilightZone", domain_name="commcouncil.scot"),
            #protocol=elbv2.ApplicationProtocol.HTTPS, # if a certificate is supplied it defaults to HTTPS allegedly
            redirect_http=True,
            certificate=cert_man.Certificate.from_certificate_arn(self, "Moodle-domain-cert", certificate_arn),
            cpu=256,                    # Default is 256
            ## Desired count set to 1, can try to 2 to test.
            ## Can be increased to 2 for subsequent deployments.
            desired_count=1,            # Default is 1 suggested is 2
            min_healthy_percent=50,     # Default is 50% of desired count
            memory_limit_mib=1024,      # Default is 512
            public_load_balancer=True,  # Default is False
            assign_public_ip=True,
            task_image_options=task_image_options,
            health_check_grace_period=Duration.seconds(900), # Default is 60
            platform_version=ecs.FargatePlatformVersion.VERSION1_4, # must specify VERSION1_4 for efs to mount
            )
        
        ##  A volume for the containers in EFS
        volume_name = "moodleVolume"        ## referenced in mount point below
        application.task_definition.add_volume(name=volume_name,
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system.file_system_id,
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=access_point.access_point_id,
                    iam="ENABLED"
                    ),
                transit_encryption="ENABLED"   # enable encryption for EFS data in transit
                )
            )
        
        ##  Mount point for volume
        application.task_definition.default_container.add_mount_points(
            ecs.MountPoint(
                container_path="/bitnami",
                read_only=False,
                source_volume=volume_name  # must match name string in add_volume
                )
            )

        ## Grant containers access to file system
        application.task_definition.add_to_task_role_policy(iam.PolicyStatement(actions=
                ['elasticfilesystem:ClientWrite',
                'elasticfilesystem:ClientRead'
                ],
                resources=[file_system.file_system_arn])
            )

        ## Connections - allows traffic between the default, automatically created security groups
        dbport = data_base.connections.default_port
        efsport = file_system.connections.default_port
        data_base.connections.allow_default_port_from(application.service)
        application.service.connections.allow_from(data_base, port_range=dbport)
        application.service.connections.allow_from(file_system, port_range=efsport)
        file_system.connections.allow_default_port_from(application.service)

        ####################
        ##### WAF stuff ####
        ####################

        waf_rules = list()
        
        """ 0. PHP Rule Set"""
        """ Contains rules that block request patterns associated with exploiting vulnerabilities specific to the use of PHP, 
        including injection of unsafe PHP functions. This can help prevent exploits that allow an attacker to remotely execute code or commands """
        aws_php_rule = waf.CfnWebACL.RuleProperty(
            name='WafPHPRule',
            priority=0,
            override_action=waf.CfnWebACL.OverrideActionProperty(count={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name='AWSManagedRulesPHPRuleSet',
                    vendor_name='AWS',
                    excluded_rules=[]
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='aws_php',
                sampled_requests_enabled=True,
            )
        )
        waf_rules.append(aws_php_rule)

        """ 1. AWS Common Rule Set """
        """ Contains rules that are generally applicable to web applications. 
        This provides protection against exploitation of a wide range of vulnerabilities, 
        including those described in OWASP publications. """
        aws_common_rule = waf.CfnWebACL.RuleProperty(
            name='WafCommonRule',
            priority=1,
            override_action=waf.CfnWebACL.OverrideActionProperty(count={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name='AWSManagedRulesCommonRuleSet',
                    vendor_name='AWS',
                    excluded_rules=[]
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='aws_common',
                sampled_requests_enabled=True,
            )
        )
        waf_rules.append(aws_common_rule)

        """ 2. SQL Injection """
        """ Contains rules that allow you to block request patterns associated with exploitation of SQL databases, 
        like SQL injection attacks. This can help prevent remote injection of unauthorized queries """
        aws_sqli_rule = waf.CfnWebACL.RuleProperty(
            name='WafSQLiRule',
            priority=2,
            override_action=waf.CfnWebACL.OverrideActionProperty(count={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name='AWSManagedRulesSQLiRuleSet',
                    vendor_name='AWS',
                    excluded_rules=[]
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='aws_sqli',
                sampled_requests_enabled=True,
            )
        )
        waf_rules.append(aws_sqli_rule)

        """ 3. Linux Rule """
        """ Contains rules that block request patterns associated with exploitation of vulnerabilities specific to Linux, including LFI attacks. 
        This can help prevent attacks that expose file contents or execute code for which the attacker should not have had access """
        aws_linux_rule = waf.CfnWebACL.RuleProperty(
            name='WafLinuxRule',
            priority=3,
            override_action=waf.CfnWebACL.OverrideActionProperty(count={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name='AWSManagedRulesLinuxRuleSet',
                    vendor_name='AWS',
                    excluded_rules=[]
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='aws_linux',
                sampled_requests_enabled=True,
            )
        )
        waf_rules.append(aws_linux_rule)

        """ 4. Bad Input Rule """
        """ Contains rules that block request patterns associated with exploitation of vulnerabilities specific to Linux, including LFI attacks. 
        This can help prevent attacks that expose file contents or execute code for which the attacker should not have had access """
        aws_bad_input_rule = waf.CfnWebACL.RuleProperty(
            name='WafBadInputRule',
            priority=4,
            override_action=waf.CfnWebACL.OverrideActionProperty(count={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name='AWSManagedRulesKnownBadInputsRuleSet',
                    vendor_name='AWS',
                    excluded_rules=[]
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='aws_badinput',
                sampled_requests_enabled=True,
            )
        )
        waf_rules.append(aws_bad_input_rule)

        """ Create the Web ACL for the WAF using the managed rule sets list (waf_rules) 
        in this case the Web ACL is "REGIONAL" as we are attaching it to the ALB """
        web_acl = waf.CfnWebACL(
            self, 'WebACL',
            default_action=waf.CfnWebACL.DefaultActionProperty(
                allow={}
            ),
            scope="REGIONAL",  
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='webACL',
                sampled_requests_enabled=True
            ),
            name=f'MoodleWAF-dev',
            rules=waf_rules
        )

        """ Associate it with the ALB arn. """
        waf.CfnWebACLAssociation(self, 'WAFACLAssociateALB',
                                 web_acl_arn=web_acl.attr_arn,
                                 resource_arn=application.load_balancer.load_balancer_arn)
        

        ## Outputs, prints output values
        CfnOutput(self, 'MOODLE-USERNAME', value='moodleadmin') 
        CfnOutput(self, 'MOODLE-PASSWORD-ARN', value=moodlepassword.secret_arn)