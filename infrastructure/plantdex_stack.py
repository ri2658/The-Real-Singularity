from pathlib import Path

from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_secretsmanager as secretsmanager,
    aws_dynamodb as dynamodb,
)
from aws_cdk.aws_apigatewayv2 import (
    HttpApi,
    HttpMethod,
    CorsPreflightOptions,
    CorsHttpMethod,
)
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from constructs import Construct


class PlantDexStack(Stack):
    """
    AWS CDK stack for deploying the PlantDex backend API.

    This stack creates:
    - A Python AWS Lambda function for handling similar-plant requests.
    - An HTTP API Gateway endpoint.
    - A GET `/similar` route connected to the Lambda function.
    - A Secrets Manager reference for the Trefle API token.
    - IAM permissions allowing Lambda to read the Trefle secret.
    - A CloudFormation output containing the deployed API URL.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        project_root = Path(__file__).resolve().parents[1]
        src_path = project_root / "src"

        # Existing Secrets Manager secret.
        # This secret should already exist in AWS Secrets Manager with name:
        # plantdex/trefle-token
        #
        # Expected secret value:
        # {"TREFLE_TOKEN":"your_real_trefle_token"}
        trefle_secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "TrefleTokenSecret",
            "plantdex/trefle-token",
        )

        cache_table = dynamodb.Table(
            self,
            "PlantDexCacheTable",
            partition_key=dynamodb.Attribute(
                name="cache_key",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Lambda function that powers the `/similar` API route.
        similar_plants_fn = lambda_.Function(
            self,
            "SimilarPlantsFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_handlers.similar_plants_handler.lambda_handler",
            code=lambda_.Code.from_asset(str(src_path)),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "TREFLE_SECRET_NAME": "plantdex/trefle-token",
                "CACHE_TABLE_NAME": cache_table.table_name,
                "CACHE_TTL_SECONDS": "86400",
            },
        )

        # Grant Lambda permission to read the Trefle token secret.
        trefle_secret.grant_read(similar_plants_fn)
        cache_table.grant_read_write_data(similar_plants_fn)

        # Public HTTP API for the PlantDex backend.
        api = HttpApi(
            self,
            "PlantDexHttpApi",
            cors_preflight=CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[
                    CorsHttpMethod.GET,
                    CorsHttpMethod.POST,
                    CorsHttpMethod.OPTIONS,
                ],
                allow_headers=["Content-Type"],
            ),
        )

        # Connect API Gateway to Lambda.
        integration = HttpLambdaIntegration(
            "SimilarPlantsIntegration",
            similar_plants_fn,
        )

        # GET /similar
        api.add_routes(
            path="/similar",
            methods=[HttpMethod.GET],
            integration=integration,
        )

        # GET /search
        api.add_routes(
            path="/search",
            methods=[HttpMethod.GET],
            integration=integration,
        )

        # GET /plants/{slug}
        api.add_routes(
            path="/plants/{slug}",
            methods=[HttpMethod.GET],
            integration=integration,
        )

        # POST /plants/{slug}/report  (proxy to Trefle species report)
        api.add_routes(
            path="/plants/{slug}/report",
            methods=[HttpMethod.POST],
            integration=integration,
        )

        # POST /plants/{slug}/corrections  (proxy to Trefle species corrections)
        api.add_routes(
            path="/plants/{slug}/corrections",
            methods=[HttpMethod.POST],
            integration=integration,
        )

        # Output the API base URL after deployment.
        CfnOutput(
            self,
            "PlantDexApiUrl",
            value=api.api_endpoint,
        )

        CfnOutput(
            self,
            "PlantDexCacheTableName",
            value=cache_table.table_name,
        )