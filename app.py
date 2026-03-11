import streamlit as st
import socket
import threading
import time
import requests
from queue import Queue

# --- 1. 基本設定（サイドバー） ---
st.set_page_config(page_title="AI Streamer 3.1 Pro", page_icon="🎙")
st.sidebar.title("🎙 AI Streamer Live Engine")
st.sidebar.info("Model: Gemini 3.1 Flash Lite")

ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("AIが喋る間隔（秒）", 10, 60, 25) # 3.1は速いので短めでもOK

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

# --- 3. AI思考エンジン：Gemini 3.1 Flash Lite 実装 ---
def generate_ai_talk_3_1():
    collected = []
    while not st.session_state.chat_queue.empty():
        collected.append(st.session_state.chat_queue.get())
    
    if collected:
        summary = "\n".join([f"- {m['user']}: {m['text']}" for m in collected])
        prompt = f"知性的で皮肉屋なAI配信者として、以下の視聴者コメントを拾って毒を吐きつつ、最近の不条理なニュースに繋げて150文字程度で喋って。セリフは「」内で。\n{summary}"
    else:
        prompt = "チャットが静かです。皮肉屋なAI配信者として、視聴者の怠慢を煽りつつ、自発的に150文字程度の鋭い独り言を言って。「」内のみ。"

    # 最新の安定版エンドポイントと3.1 Flash Liteモデルを指定
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={ST_GEMINI_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        res_json = res.json()
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"（エラー: {res_json.get('error', {}).get('message', 'AIが沈黙しました')}）"
    except Exception as e:
        return f"（通信エラー: {str(e)}）"

# --- 4. UI 表示 ---
st.title("🤖 AI Streamer 3.1 Flash Lite")

col1, col2 = st.columns(2)
col1.metric("Twitch同期", st.session_state.conn_status)
col2.metric("待機中コメント", st.session_state.chat_queue.qsize())

# 自動リフレッシュ JS
st.components.v1.html(f"""
    <script>
    setTimeout(function(){{
        window.parent.document.querySelector('button[kind="primary"]').click();
    }}, {refresh_rate * 1000});
    </script>
""", height=0)

if st.button("🎙 トーク生成（自動巡回中）", type="primary"):
    with st.spinner("Gemini 3.1が思考中..."):
        talk = generate_ai_talk_3_1()
        if talk:
            st.session_state.chat_history.append(talk)
            clean_text = talk.replace("「", "").replace("」", "").replace("\n", " ")
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{clean_text}");
                msg.lang = "ja-JP";
                msg.pitch = 0.75; // 少し低めの皮肉っぽい声
                msg.rate = 1.1;  // 少し早口
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)

st.divider()
for m in reversed(st.session_state.chat_history):
    st.chat_message("assistant", avatar="🤖").write(m)
