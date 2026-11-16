#!/usr/bin/env python3
"""CDK app that deploys the Burgers PINN site."""

import aws_cdk as cdk

from burgers_site_stack import BurgersSiteStack

app = cdk.App()
BurgersSiteStack(app, "BurgersSiteStack")
app.synth()
