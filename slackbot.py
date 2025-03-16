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
BOT_USER_ID = os.getenv("BOT_USER_ID")  # Bot の ID を環境変数に設定

# DynamoDB & Slack クライアントの初期化
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)
client = WebClient(token=SLACK_BOT_TOKEN)

def lambda_handler(event, context):
    """Lambda のメイン処理"""
    logger.info("==== Lambda Invoked ====")
    logger.info(f"Received event: {json.dumps(event, indent=2)}")

    body = json.loads(event["body"])
    slack_event = body.get("event", {})

    text = slack_event.get("text", "").strip()
    channel = slack_event.get("channel", "")

    logger.info(f"Extracted text before cleaning: {text}")

    # 🔹 メンション (`<@BOT_USER_ID>`) を削除
    bot_mention = f"<@{BOT_USER_ID}>"
    if text.startswith(bot_mention):
        text = text.replace(bot_mention, "").strip()
    
    logger.info(f"Processed text after cleaning: {text}")

    # コマンドの処理
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
    elif text == "!list":
        response = list_words()
    elif text.startswith("!deleteword "):
        keyword = text.split(" ", 1)[1].strip()
        response = delete_word(keyword)
    else:
        response = "⚠️ 無効なコマンドです"

    send_message(channel, response)
    return {"statusCode": 200, "body": "OK"}

def get_word(keyword):
    """DynamoDB からキーワードを取得"""
    response = table.get_item(Key={"keyword": keyword})
    description = response.get("Item", {}).get("description", "わかりませーん")
    logger.info(f"Fetched from DB: {keyword} -> {description}")
    return description

def add_word(keyword, description):
    """DynamoDB にキーワードを追加"""
    table.put_item(Item={"keyword": keyword, "description": description})
    logger.info(f"Added to DB: {keyword} -> {description}")
    return f"✅ `{keyword}` を登録しました！"

def update_word(keyword, description):
    """DynamoDB のデータを更新"""
    table.update_item(
        Key={"keyword": keyword},
        UpdateExpression="SET description = :desc",
        ExpressionAttributeValues={":desc": description}
    )
    logger.info(f"Updated DB: {keyword} -> {description}")
    return f"🔄 `{keyword}` の情報を更新しました！"

def list_words():
    """DynamoDB からすべてのキーワードを取得"""
    try:
        response = table.scan(ProjectionExpression="keyword")
        words = [item["keyword"] for item in response.get("Items", [])]
        if not words:
            return "⚠️ 登録されているキーワードがありません。"
        return "📋 登録済みのキーワード:\n- " + "\n- ".join(words)
    except Exception as e:
        logger.error(f"Failed to list words: {str(e)}")
        return "⚠️ キーワード一覧の取得に失敗しました。"

def delete_word(keyword):
    """DynamoDB から指定したキーワードを削除"""
    try:
        response = table.delete_item(Key={"keyword": keyword})
        logger.info(f"Deleted word: {keyword}")
        return f"✅ '{keyword}' を削除しました！"
    except Exception as e:
        logger.error(f"Failed to delete word: {str(e)}")
        return f"⚠️ '{keyword}' の削除に失敗しました。"

def send_message(channel, text):
    """Slack にメッセージを送信"""
    client.chat_postMessage(channel=channel, text=text)
    logger.info(f"Message sent to {channel}: {text}")
