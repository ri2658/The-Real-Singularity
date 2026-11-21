#!/usr/bin/env python3
"""CDK app for the website: one stack, BurgersSiteStack (S3 + CloudFront)."""

import aws_cdk as cdk

from burgers_site_stack import BurgersSiteStack

app = cdk.App()
BurgersSiteStack(app, "BurgersSiteStack")
app.synth()
