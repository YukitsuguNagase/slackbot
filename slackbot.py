import json
import os
import boto3
import logging
from slack_sdk import WebClient

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# 環境変数の取得
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")
BOT_USER_ID = os.getenv("BOT_USER_ID")
ASYNC_LAMBDA_NAME = os.getenv("ASYNC_LAMBDA_NAME")  # 非同期処理Lambdaの名前

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)
client = WebClient(token=SLACK_BOT_TOKEN)
lambda_client = boto3.client("lambda")

def lambda_handler(event, context):
    logger.info("==== Lambda Invoked ====")
    body = json.loads(event["body"])
    slack_event = body.get("event", {})

    if "challenge" in body:
        return {"statusCode": 200, "body": json.dumps({"challenge": body["challenge"]})}

    text = slack_event.get("text", "").strip()
    channel = slack_event.get("channel", "")

    bot_mention = f"<@{BOT_USER_ID}>"
    if text.startswith(bot_mention):
        text = text.replace(bot_mention, "").strip()

    # 非同期Lambdaを呼び出す（イベント渡し）
    lambda_client.invoke(
        FunctionName=ASYNC_LAMBDA_NAME,
        InvocationType='Event',
        Payload=json.dumps({"text": text, "channel": channel})
    )

    # 即座にSlackにレスポンスを返す
    return {"statusCode": 200, "body": "OK"}