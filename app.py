import streamlit as st
import socket
import threading
import time
import requests
from queue import Queue

# --- 1. 基本設定（サイドバー） ---
st.set_page_config(page_title="AI Streamer v3.1", page_icon="🎙")
st.sidebar.title("🎙 AI Streamer Live Engine")

ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("AIが喋る間隔（秒）", 10, 60, 25)

# セッション管理
if "chat_queue" not in st.session_state:
    st.session_state.chat_queue = Queue()
if "conn_status" not in st.session_state:
    st.session_state.conn_status = "🔴 未接続"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 2. バックグラウンド：Twitch常時同期スレッド ---
def twitch_listener(channel, token, queue):
    while True:
        try:
            sock = socket.socket()
            sock.settimeout(10.0)
            sock.connect(("irc.chat.twitch.tv", 6667))
            auth_token = token if token.startswith("oauth:") else f"oauth:{token}"
            sock.send(f"PASS {auth_token}\r\n".encode("utf-8"))
            sock.send(f"NICK {channel}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{channel}\r\n".encode("utf-8"))
            sock.send("CAP REQ :twitch.tv/tags twitch.tv/commands\r\n".encode("utf-8"))
            st.session_state.conn_status = "🟢 常時同期中"
            while True:
                data = sock.recv(2048).decode("utf-8")
                if not data: break
                if data.startswith("PING"):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                elif "PRIVMSG" in data:
                    user = data.split("!")[0][1:]
                    msg = data.split(f"#{channel} :", 1)[1].strip()
                    queue.put({"user": user, "text": msg})
        except:
            st.session_state.conn_status = "🔴 再接続中..."
            time.sleep(5)

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    if "thread_started" not in st.session_state:
        t = threading.Thread(target=twitch_listener, args=(TW_CHANNEL, TW_ACCESS_TOKEN, st.session_state.chat_queue), daemon=True)
        t.start()
        st.session_state.thread_started = True

# --- 3. AI思考エンジン：自動モデル選別機能 ---
def generate_ai_talk_final():
    collected = []
    while not st.session_state.chat_queue.empty():
        collected.append(st.session_state.chat_queue.get())
    
    if collected:
        summary = "\n".join([f"- {m['user']}: {m['text']}" for m in collected])
        prompt = f"知性的で皮肉屋なAI配信者として、視聴者コメントを拾って毒を吐き、最近の不条理な話題に繋げて150文字程度で喋って。セリフは「」内で。\n{summary}"
    else:
        prompt = "チャットが静かです。皮肉屋なAI配信者として、視聴者の怠慢を煽りつつ、鋭い独り言を150文字程度で言って。「」内のみ。"

    # 試行するモデルの優先順位リスト
    models_to_try = [
        "gemini-3.1-flash-lite-preview", # 2026年最新本命
        "gemini-3-flash-preview",      # 準最新
        "gemini-2.0-flash"             # 鉄板の安定版
    ]

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={ST_GEMINI_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in [
                "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", 
                "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"
            ]]
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            res_json = res.json()
            if 'candidates' in res_json:
                st.sidebar.write(f"使用中モデル: {model}") # デバッグ用
                return res_json['candidates'][0]['content']['parts'][0]['text']
        except:
            continue
    
    return "（全モデルでエラーよ。APIキーを見直してちょうだい。）"

# --- 4. UI 表示 ---
st.title("🤖 AI Streamer Pro：安定稼働モード")

col1, col2 = st.columns(2)
col1.metric("Twitch同期", st.session_state.conn_status)
col2.metric("待機中コメント", st.session_state.chat_queue.qsize())

st.components.v1.html(f"""
    <script>
    setTimeout(function(){{ window.parent.document.querySelector('button[kind="primary"]').click(); }}, {refresh_rate * 1000});
    </script>
""", height=0)

if st.button("🎙 トーク生成（自動巡回中）", type="primary"):
    with st.spinner("AIが最適な脳（モデル）を選別中..."):
        talk = generate_ai_talk_final()
        if talk:
            st.session_state.chat_history.append(talk)
            clean_text = talk.replace("「", "").replace("」", "").replace("\n", " ")
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{clean_text}");
                msg.lang = "ja-JP"; msg.pitch = 0.8; msg.rate = 1.1;
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)

st.divider()
for m in reversed(st.session_state.chat_history):
    st.chat_message("assistant", avatar="🤖").write(m)
