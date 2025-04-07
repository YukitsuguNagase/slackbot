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
    text = event["text"].strip()
    channel = event["channel"]

    # コマンドごとの処理を辞書で定義
    command_map = {
        "!word": {"func": get_word, "min_args": 1, "usage": "!word <keyword>"},
        "!addword": {"func": add_word, "min_args": 2, "usage": "!addword <keyword> <description>"},
        "!update": {"func": update_word, "min_args": 2, "usage": "!update <keyword> <description>"},
        "!deleteword": {"func": delete_word, "min_args": 1, "usage": "!deleteword <keyword>"},
        "!list": {"func": list_words, "min_args": 0, "usage": "!list"},
    }

    response = "⚠️ 無効なコマンドです"
    for command, info in command_map.items():
        if text.startswith(command):
            args = text[len(command):].strip()
            if info["min_args"] == 0:
                response = info["func"]()
            elif info["min_args"] == 1:
                if not args:
                    response = f"⚠️ 正しい形式: `{info['usage']}`"
                else:
                    response = info["func"](args)
            elif info["min_args"] == 2:
                parts = args.split(" ", 1)
                if len(parts) < 2:
                    response = f"⚠️ 正しい形式: `{info['usage']}`"
                else:
                    response = info["func"](parts[0], parts[1])
            break

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
    return f"✅ `{keyword}` を削除しました！"

def send_message(channel, text):
    client.chat_postMessage(channel=channel, text=text)
