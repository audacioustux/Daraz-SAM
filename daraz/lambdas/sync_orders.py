import os
from typing import Any
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools import Logger, Tracer, Metrics
from common.daraz_sdk import DarazOAuthTokens, DarazRequest, DarazClient
from common.config import API_URL, APP_KEY, APP_SECRET, APP_TOKENS_SSM_PATH

tracer = Tracer()
logger = Logger()
metrics = Metrics()

# print logger level
logger.info("Logger level: %s", logger.log_level)

@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Sync orders from Daraz"""

    # get access token
    access_token = DarazOAuthTokens.from_ssm(APP_TOKENS_SSM_PATH).access_token

    # create client
    client = DarazClient(API_URL, APP_KEY, APP_SECRET)

    # get orders
    request = DarazRequest('/orders/get','GET')
    request.add_api_param('created_after', "2021-01-01T00:00:00+06:00")
    response: Any = client.execute(request, access_token)
    logger.debug(response.body)

    # get all order ids
    order_ids = [order['order_id'] for order in response.body['data']['orders']]

    # process each order
    for order_id in order_ids:
        request = DarazRequest('/order/items/get','GET')
        request.add_api_param('order_id', order_id)
        response = client.execute(request, access_token)
        logger.debug(response.body)

        # log warning if ["code"] is not 0, and skip to next order
        if response.body["code"] != "0":
            logger.warning(response.body)
            continue

        # get order items
        order_items = response.body['data']
        for item in order_items:
            logger.info({
                "order_id": item["order_id"],
                "buyer_id": item["buyer_id"],
                "sku": item["sku"],
                "shop_sku": item["shop_sku"],
                "name": item["name"],
                "status": item["status"],
                "digital_delivery_info": item["digital_delivery_info"],
            })

    return {"status": "success"}
