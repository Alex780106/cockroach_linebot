from __future__ import unicode_literals
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import requests
import json
import configparser
import os
from urllib import parse
app = Flask(__name__, static_url_path='/static')
UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif'])


config = configparser.ConfigParser()
config.read('config.ini')

line_bot_api = LineBotApi(config.get('line-bot', 'channel_access_token'))
handler = WebhookHandler(config.get('line-bot', 'channel_secret'))
my_line_id = config.get('line-bot', 'my_line_id')
end_point = config.get('line-bot', 'end_point')
line_login_id = config.get('line-bot', 'line_login_id')
line_login_secret = config.get('line-bot', 'line_login_secret')
my_phone = config.get('line-bot', 'my_phone')
HEADER = {
    'Content-type': 'application/json',
    'Authorization': F'Bearer {config.get("line-bot", "channel_access_token")}'
}


@app.route("/", methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        print('OK')
        return 'ok'
    body = request.json
    events = body["events"]
    print(body)
    if "replyToken" in events[0]:
        payload = dict()
        replyToken = events[0]["replyToken"]
        payload["replyToken"] = replyToken
        if events[0]["type"] == "message":
            if events[0]["message"]["type"] == "text":
                text = events[0]["message"]["text"]

                if text == "我的名":
                    payload["messages"] = [getNameEmojiMessage()]
                elif text == "圖片":
                    payload["messages"] = [getCockroachImageMessage()]
                elif text == "quoda":
                    payload["messages"] = [
                            {
                                "type": "text",
                                "text": getTotalSentMessageCount()
                            }
                        ]
                else:
                    payload["messages"] = [
                            {
                                "type": "text",
                                "text": text
                            }
                        ]
                replyMessage(payload)
            else:
                data = json.loads(events[0]["postback"]["data"])
                action = data["action"]
                if action == "get_near":
                    data["action"] = "get_detail"
                elif action == "get_detail":
                    del data["action"]
                    payload["messages"] = [getCockroachImageMessage()]
                replyMessage(payload)

    return 'OK'


@app.route("/callback", methods=['POST'])
def callback():
    print('callback')
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)

    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def pretty_echo(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text)
        )


@app.route("/sendTextMessageToMe", methods=['POST'])
def sendTextMessageToMe():
    pushMessage({})
    return 'OK'


def getNameEmojiMessage():
    lookUpStr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    productId = "5ac21a8c040ab15980c9b43f"
    name = "Alex"
    message = dict()
    message["type"] = "text"
    message["text"] = "".join("$" for r in range(len(name)))
    emojis_list = list()
    for i, nChar in enumerate(name):
        emojis_list.append(
            {
              "index": i,
              "productId": productId,
              "emojiId": f"{lookUpStr.index(nChar) + 1 :03}"
            }
        )
    message["emojis"] = emojis_list
    return message

def getPlayStickerMessage():
    message = dict()
    message["type"] = "sticker"
    message["packageId"] = "446"
    message["stickerId"] = "1988"
    return message


def getCockroachImageMessage(originalContentUrl=F"{end_point}/static/cockroach.jpeg"):
    return getImageMessage(originalContentUrl)


def getImageMessage(originalContentUrl):
    message = {
      "type": "image",
      "originalContentUrl": originalContentUrl,
      "previewImageUrl": originalContentUrl
    }

    return message


def replyMessage(payload):
    r = requests.post('https://api.line.me/v2/bot/message/reply', data=json.dumps(payload), headers=HEADER)
    print(r.content)
    return 'OK'


def pushMessage(payload):
    r = requests.post('https://api.line.me/v2/bot/message/push', data=json.dumps(payload), headers=HEADER)
    print(r.content)
    return 'OK'


def getTotalSentMessageCount():
    r = requests.get('https://api.line.me/v2/bot/message/quota/consumption', headers=HEADER)
    print(r.json())
    return r.json()['totalUsage']

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload_file', methods=['POST'])
def upload_file():
    payload = dict()
    if request.method == 'POST':
        file = request.files['file']
        print("json:", request.json)
        form = request.form
        age = form['age']
        gender = ("男" if form['gender'] == "M" else "女") + "性"
        if file:
            filename = file.filename
            img_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(img_path)
            print(img_path)
            payload["to"] = my_line_id
            payload["messages"] = [getImageMessage(F"{end_point}/{img_path}"),
                {
                    "type": "text",
                    "text": F"年紀：{age}\n性別：{gender}"
                }
            ]
            pushMessage(payload)
    return 'OK'


@app.route('/line_login', methods=['GET'])
def line_login():
    if request.method == 'GET':
        code = request.args.get("code", None)
        state = request.args.get("state", None)

        if code and state:
            HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}
            url = "https://api.line.me/oauth2/v2.1/token"
            FormData = {"grant_type": 'authorization_code', "code": code, "redirect_uri": F"{end_point}/line_login", "client_id": line_login_id, "client_secret":line_login_secret}
            data = parse.urlencode(FormData)
            content = requests.post(url=url, headers=HEADERS, data=data).text
            content = json.loads(content)
            url = "https://api.line.me/v2/profile"
            HEADERS = {'Authorization': content["token_type"]+" "+content["access_token"]}
            content = requests.get(url=url, headers=HEADERS).text
            content = json.loads(content)
            name = content["displayName"]
            userID = content["userId"]
            pictureURL = content["pictureUrl"]
            statusMessage = content["statusMessage"]
            print(content)
            return render_template('profile.html', name=name, pictureURL=
                                   pictureURL, userID=userID, statusMessage=
                                   statusMessage)
        else:
            return render_template('login.html', client_id=line_login_id,
                                   end_point=end_point)


if __name__ == "__main__":
    app.debug = True
    app.run()
