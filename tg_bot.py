import requests

API_TOKEN = 'bot-token-here'
CHAT_ID = 'chat-id-here'
API_URL = f'https://api.telegram.org/bot{API_TOKEN}/sendMessage'

def sendToTelegram(msg):
    try:
        response = requests.post(API_URL, json={'chat_id': CHAT_ID, 'text': msg})
        return response.text
    except Exception as e:
        return e
