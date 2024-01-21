from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics
from common.config import API_URL, APP_KEY, APP_SECRET, APP_CODE_SSM_PATH, APP_TOKENS_SSM_PATH
from common.daraz_sdk import DarazClient, DarazOAuthTokens

tracer = Tracer()
logger = Logger()
metrics = Metrics()

app = APIGatewayRestResolver(strip_prefixes=["/daraz"])

@app.get("/hello")
@tracer.capture_method
def hello():
    # adding custom metrics
    # See: https://awslabs.github.io/aws-lambdacan no access a module with __init__ file-powertools-python/latest/core/metrics/
    metrics.add_metric(name="HelloWorldInvocations", unit=MetricUnit.Count, value=1)

    # structured log
    # See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/logger/
    logger.info("Hello world API - HTTP 200")
    return {"message": "hello world"}

@app.get("/oauth/callback")
@tracer.capture_method
def oauth_callback() -> dict:
    """Persist OAuth code"""

    event = app.current_event

    code = event["queryStringParameters"]["code"]

    if not code:
        raise Exception("code is not present")

    # generate tokens
    client = DarazClient(API_URL, APP_KEY, APP_SECRET)
    tokens = DarazOAuthTokens.from_code(code, client)

    # save both tokens in SSM
    tokens.put_in_ssm(APP_TOKENS_SSM_PATH)

    # Store code in AWS SSM
    ssm = boto3.client("ssm")
    ssm.put_parameter(
        Name=APP_CODE_SSM_PATH,
        Description="Daraz oauth code",
        Value=code,
        Type="SecureString",
        Overwrite=True,
    )

    return tokens.to_dict()

# Enrich logging with contextual information from Lambda
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
# Adding tracer
# See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/tracer/
@tracer.capture_lambda_handler
# ensures metrics are flushed upon request completion/failure and capturing ColdStart metric
@metrics.log_metrics
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
