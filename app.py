import streamlit as st
import socket
import threading
import time
import requests
from queue import Queue

# --- 1. 基本設定（サイドバー） ---
st.set_page_config(page_title="AI Streamer Pro", page_icon="🎙", layout="wide")

# 【修正】文字を見やすくするためのCSS。背景を少し明るく、文字を白に固定します。
st.markdown("""
    <style>
    [data-testid="stChatMessage"] {
        background-color: #262730 !important;
        border: 1px solid #464b5d;
        color: white !important;
    }
    [data-testid="stChatMessage"] p {
        color: #ffffff !important;
        font-size: 1.1rem;
    }
    .stMetric { background-color: #0e1117; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

st.sidebar.title("🎙 AI Streamer Setting")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("自動更新（秒）", 10, 60, 25)

# セッション管理
if "chat_queue" not in st.session_state: st.session_state.chat_queue = Queue()
if "conn_status" not in st.session_state: st.session_state.conn_status = "🔴 未接続"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "ai_mood" not in st.session_state: st.session_state.ai_mood = "普通"

# --- 2. Twitch監視（安定化） ---
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
            st.session_state.conn_status = "🟢 同期中"
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
            st.session_state.conn_status = "🔴 再接続中"
            time.sleep(5)

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN and "thread_started" not in st.session_state:
    t = threading.Thread(target=twitch_listener, args=(TW_CHANNEL, TW_ACCESS_TOKEN, st.session_state.chat_queue), daemon=True)
    t.start()
    st.session_state.thread_started = True

# --- 3. AI思考エンジン（エラーログ詳細化） ---
def generate_ai_talk():
    collected = []
    while not st.session_state.chat_queue.empty():
        collected.append(st.session_state.chat_queue.get())
    
    if collected:
        summary = "\n".join([f"- {m['user']}: {m['text']}" for m in collected])
        prompt = f"皮肉屋なAI配信者として、視聴者「{collected[0]['user']}」のコメント『{collected[0]['text']}』を拾い、その裏にある人間の滑稽さを指摘しつつ、150文字程度で毒を吐いて。セリフは「」内のみ。"
    else:
        prompt = "チャットが静かです。皮肉屋AIとして、視聴者の無関心を煽りつつ、最近の不条理なニュースを一つ挙げて150文字程度で持論を語って。「」内のみ。"

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={ST_GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in [
            "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", 
            "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"
        ]]
    }
    try:
        res = requests.post(url, json=payload, timeout=15)
        res_json = res.json()
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        elif 'error' in res_json:
            return f"（APIエラー: {res_json['error']['message']}）"
        else:
            return "（AIが沈黙。過激すぎたかしら？）"
    except Exception as e:
        return f"（接続エラー: 通信が途切れました）"

def run_ai_cycle():
    talk = generate_ai_talk()
    if talk:
        st.session_state.chat_history.append(talk)
        st.session_state.last_talk = talk.replace("「", "").replace("」", "").replace("\n", " ")

# --- 4. メイン画面 ---
st.title("🤖 AI Streamer Pro")

c1, c2 = st.columns(2)
c1.metric("Twitch同期", st.session_state.conn_status)
c2.metric("未処理コメント", st.session_state.chat_queue.qsize())

st.divider()

# トーク履歴（ここが「見にくい」の修正ポイント）
for m in reversed(st.session_state.chat_history[-10:]):
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(m)

# 操作系
if st.button("🎙 話題を更新（自動巡回中）", type="primary", on_click=run_ai_cycle):
    pass

# --- 5. JS (音声・更新) ---
if "last_talk" in st.session_state and st.session_state.last_talk:
    st.components.v1.html(f"""
        <script>
        var msg = new SpeechSynthesisUtterance("{st.session_state.last_talk}");
        msg.lang = "ja-JP"; msg.pitch = 0.8; msg.rate = 1.1;
        window.speechSynthesis.speak(msg);
        </script>
    """, height=0)
    st.session_state.last_talk = None

st.components.v1.html(f"""
    <script>
    setTimeout(function(){{ window.parent.document.querySelector('button[kind="primary"]').click(); }}, {refresh_rate * 1000});
    </script>
""", height=0)
