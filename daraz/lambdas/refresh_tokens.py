from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools import Logger, Tracer, Metrics
from common.config import API_URL, APP_KEY, APP_SECRET, APP_TOKENS_SSM_PATH
from common.daraz_sdk import DarazOAuthTokens, DarazClient

tracer = Tracer()
logger = Logger()
metrics = Metrics()

@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Refresh access and refresh tokens"""

    # generate tokens
    client = DarazClient(API_URL, APP_KEY, APP_SECRET)
    token = DarazOAuthTokens.from_refresh_token_in_ssm(APP_TOKENS_SSM_PATH, client)
    logger.debug(token.to_dict())

    # save both tokens in SSM
    token.put_in_ssm(APP_TOKENS_SSM_PATH)

    return {"status": "success"}