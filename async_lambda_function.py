import json
import os
import boto3
import logging
from slack_sdk import WebClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)
client = WebClient(token=SLACK_BOT_TOKEN)

def lambda_handler(event, context):
    text = event["text"]
    channel = event["channel"]

    if text.startswith("!word "):
        keyword = text.split(" ", 1)[1].strip()
        response = get_word(keyword)
    elif text.startswith("!addword "):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            response = "⚠️ 正しい形式: `!addword <keyword> <description>`"
        else:
            keyword, description = parts[1], parts[2]
            response = add_word(keyword, description)
    elif text.startswith("!update "):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            response = "⚠️ 正しい形式: `!update <keyword> <description>`"
        else:
            keyword, description = parts[1], parts[2]
            response = update_word(keyword, description)
    elif text == "!list":#登録済みキーワードの一覧を表示
        response = list_words()
    elif text.startswith("!deleteword "):
        keyword = text.split(" ", 1)[1].strip()
        response = delete_word(keyword)
    else:
        response = "⚠️ 無効なコマンドです"

    send_message(channel, response)

def get_word(keyword):
    response = table.get_item(Key={"keyword": keyword})
    return response.get("Item", {}).get("description", "わかりませーん")

def add_word(keyword, description):
    table.put_item(Item={"keyword": keyword, "description": description})
    return f"✅ `{keyword}` を登録しました！"

def update_word(keyword, description):
    table.update_item(
        Key={"keyword": keyword},
        UpdateExpression="SET description = :desc",
        ExpressionAttributeValues={":desc": description}
    )
    return f"🔄 `{keyword}` の情報を更新しました！"

def list_words():
    response = table.scan(ProjectionExpression="keyword")
    words = [item["keyword"] for item in response.get("Items", [])]
    if not words:
        return "⚠️ 登録されているキーワードがありません。"
    return "📋 登録済みのキーワード:\n- " + "\n- ".join(words)

def delete_word(keyword):
    table.delete_item(Key={"keyword": keyword})
    return f"✅ '{keyword}' を削除しました！"

def send_message(channel, text):
    client.chat_postMessage(channel=channel, text=text)
