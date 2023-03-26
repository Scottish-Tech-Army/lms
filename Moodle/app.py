#!/usr/bin/env python3
import os

import aws_cdk as cdk

from moodle_serverless.moodle_serverless_stack import MoodleServerlessStackV2


app = cdk.App()

props = {
    "domain_name": app.node.try_get_context("domain_name"),
    "hosted_zone_id": app.node.try_get_context("hosted_zone_id"),
    "hosted_zone_name": app.node.try_get_context("hosted_zone_name"),
    "domain_certificate_arn": app.node.try_get_context("domain_certificate_arn")
    }

MoodleServerlessStackV2(app, "MoodleServerlessStackV2",
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */

    env=cdk.Environment(account='131458236732', region='eu-west-2'),
    props=props

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
