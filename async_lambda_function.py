import os
import time
import boto3
import logging
import random
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
        "!word": {
            "func": get_word,
            "min_args": 1,
            "usage": "!word <keyword>",
            "exact": False
        },
        "!addword": {
            "func": add_word,
            "min_args": 2,
            "usage": "!addword <keyword> <description>",
            "exact": False
        },
        "!update": {
            "func": update_word,
            "min_args": 2,
            "usage": "!update <keyword> <description>",
            "exact": False
        },
        "!deleteword": {
            "func": delete_word,
            "min_args": 1,
            "usage": "!deleteword <keyword>",
            "exact": False
        },
        "!list": {
            "func": list_words,
            "min_args": 0,
            "usage": "!list",
            "exact": True
        },
        "!search": {
            "func": search_words,
            "min_args": 1,
            "usage": "!search <keyword_part>",
            "exact": False
        },
        "!random": {
            "func": random_words,
            "min_args": 0,
            "usage": "!random",
            "exact": True
        }
    }

    response = "⚠️ 無効なコマンドです"
    for command, conf in command_map.items():
        if conf.get("exact") and text == command:
            response = conf["func"]()
            break
        elif not conf.get("exact") and text.startswith(command):
            args = text[len(command):].strip()
            if conf["min_args"] == 0:
                response = conf["func"]()
            elif conf["min_args"] == 1:
                if not args:
                    response = f"⚠️ 正しい形式: `{conf['usage']}`"
                else:
                    response = conf["func"](args)
            elif conf["min_args"] == 2:
                parts = args.split(" ", 1)
                if len(parts) < 2:
                    response = f"⚠️ 正しい形式: `{conf['usage']}`"
                else:
                    response = conf["func"](parts[0], parts[1])
            break

    send_message(channel, response)

def get_word(keyword):
    response = table.get_item(Key={"keyword": keyword})
    return response.get("Item", {}).get("description", "わかりませーん")

def add_word(keyword, description):
    created_at = int(time.time())
    table.put_item(Item={
        "keyword": keyword,
        "description": description,
        "created_at": created_at
    })
    return f"✅ `{keyword}` を登録しました！"

def update_word(keyword, description):
    table.update_item(
        Key={"keyword": keyword},
        UpdateExpression="SET description = :desc",
        ExpressionAttributeValues={":desc": description}
    )
    return f"🔄 `{keyword}` の情報を更新しました！"

def list_words():
    try:
        response = table.scan(ProjectionExpression="keyword, created_at")
        items = response.get("Items", [])

        sorted_items = sorted(
            items,
            key=lambda x: x.get("created_at", 0),
            reverse=True
        )[:10]

        if not sorted_items:
            return "⚠️ 登録されているキーワードがありません。"

        words = [item["keyword"] for item in sorted_items]
        return "🆕 最近登録されたキーワード:\n- " + "\n- ".join(words)

    except Exception as e:
        logger.error(f"Failed to list words: {str(e)}")
        return "⚠️ キーワード一覧の取得に失敗しました。"

def delete_word(keyword):
    table.delete_item(Key={"keyword": keyword})
    return f"✅ `{keyword}` を削除しました！"

def search_words(part):
    try:
        response = table.scan(ProjectionExpression="keyword")
        matches = [item["keyword"] for item in response.get("Items", []) if part.lower() in item["keyword"].lower()]
        if not matches:
            return "🔍 一致するキーワードが見つかりませんでした。"
        return "🔍 部分一致したキーワード:\n- " + "\n- ".join(matches)
    except Exception as e:
        logger.error(f"Failed to search keywords: {str(e)}")
        return "⚠️ 検索中にエラーが発生しました。"

def random_words():
    try:
        response = table.scan(ProjectionExpression="keyword")
        items = response.get("Items", [])
        if not items:
            return "⚠️ 登録されているキーワードがありません。"
        selected = random.sample(items, min(10, len(items)))
        keywords = [item["keyword"] for item in selected]
        return "🎲 ランダムなキーワード:\n- " + "\n- ".join(keywords)
    except Exception as e:
        logger.error(f"Failed to get random keywords: {str(e)}")
        return "⚠️ ランダム取得中にエラーが発生しました。"

def send_message(channel, text):
    client.chat_postMessage(channel=channel, text=text)
