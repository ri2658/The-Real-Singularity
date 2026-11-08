#!/usr/bin/env python3
"""CDK app for the Burgers page only. Does not deploy the PlantDex API."""

import aws_cdk as cdk

from burgers_site_stack import BurgersSiteStack

app = cdk.App()
BurgersSiteStack(app, "BurgersSiteStack")
app.synth()
