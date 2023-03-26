import aws_cdk as core
import aws_cdk.assertions as assertions

from moodle_serverless.moodle_serverless_stack import MoodleServerlessStackV2
import aws_cdk as cdk

props = {
    "domain_name": "commcouncil.scot",
    "hosted_zone_id": "Z00217581OBDF54QYM4OF",
    "hosted_zone_name": "commcouncil.scot",
    "domain_certificate_arn": "arn:aws:acm:eu-west-2:131458236732:certificate/34bf02e0-4845-4e79-8036-9fb6dd0a8c4c"
    }

def test_vpc_exists():
    app = cdk.App()
    test_stack = MoodleServerlessStackV2(app, "MoodleServerlessStackV2", env=cdk.Environment(account='131458236732', region='eu-west-2'), props=props)
    template = assertions.Template.from_stack(test_stack)
    # Assert that we have created only one VPC
    template.resource_count_is("AWS::EC2::VPC", 1)

def test_vpc_has_four_subnets():
    app = cdk.App()
    test_stack = MoodleServerlessStackV2(app, "MoodleServerlessStackV2", env=cdk.Environment(account='131458236732', region='eu-west-2'), props=props)
    template = assertions.Template.from_stack(test_stack)
    # Assert we have only four subnets
    template.resource_count_is("AWS::EC2::Subnet", 4)

def test_vpc_has_public_subnets():
    app = cdk.App()
    test_stack = MoodleServerlessStackV2(app, "MoodleServerlessStackV2", env=cdk.Environment(account='131458236732', region='eu-west-2'), props=props)
    template = assertions.Template.from_stack(test_stack)
    # Assert we have a public subnet
    template.has_resource_properties("AWS::EC2::Subnet", {"MapPublicIpOnLaunch": True})

def test_vpc_has_private_subnets():
    app = cdk.App()
    test_stack = MoodleServerlessStackV2(app, "MoodleServerlessStackV2", env=cdk.Environment(account='131458236732', region='eu-west-2'), props=props)
    template = assertions.Template.from_stack(test_stack)
    # Assert we have a private subnet
    template.has_resource_properties("AWS::EC2::Subnet", {"MapPublicIpOnLaunch": False})

def test_vpc_has_two_public_subnets():
    app = cdk.App()
    test_stack = MoodleServerlessStackV2(app, "MoodleServerlessStackV2", env=cdk.Environment(account='131458236732', region='eu-west-2'), props=props)
    template = assertions.Template.from_stack(test_stack)
    # Assert we have a public subnet 1
    template.has_resource_properties("AWS::EC2::Subnet", {"Tags": [
     {
      "Key": "aws-cdk:subnet-name",
      "Value": "Public"
     },
     {
      "Key": "aws-cdk:subnet-type",
      "Value": "Public"
     },
     {
      "Key": "Name",
      "Value": "MoodleServerlessStackV2/Vpc/PublicSubnet1"
     }
    ]})

    # Assert we have a public subnet 2
    template.has_resource_properties("AWS::EC2::Subnet", {"Tags": [
     {
      "Key": "aws-cdk:subnet-name",
      "Value": "Public"
     },
     {
      "Key": "aws-cdk:subnet-type",
      "Value": "Public"
     },
     {
      "Key": "Name",
      "Value": "MoodleServerlessStackV2/Vpc/PublicSubnet2"
     }
    ]})

def test_vpc_has_two_private_subnets():
    app = cdk.App()
    test_stack = MoodleServerlessStackV2(app, "MoodleServerlessStackV2", env=cdk.Environment(account='131458236732', region='eu-west-2'), props=props)
    template = assertions.Template.from_stack(test_stack)
    # Assert we have a private subnet 1
    template.has_resource_properties("AWS::EC2::Subnet", {"Tags": [
     {
      "Key": "aws-cdk:subnet-name",
      "Value": "Private"
     },
     {
      "Key": "aws-cdk:subnet-type",
      "Value": "Private"
     },
     {
      "Key": "Name",
      "Value": "MoodleServerlessStackV2/Vpc/PrivateSubnet1"
     }
    ]})

    # Assert we have a private subnet 2
    template.has_resource_properties("AWS::EC2::Subnet", {"Tags": [
     {
      "Key": "aws-cdk:subnet-name",
      "Value": "Private"
     },
     {
      "Key": "aws-cdk:subnet-type",
      "Value": "Private"
     },
     {
      "Key": "Name",
      "Value": "MoodleServerlessStackV2/Vpc/PrivateSubnet2"
     }
    ]})

    





