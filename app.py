import streamlit as st
import socket
import threading
import time
import requests
from queue import Queue
import json

# --- 1. 基本設定 ---
st.set_page_config(page_title="AI Streamer Pro v2.6", page_icon="🎙", layout="wide")

# カスタムCSSで配信画面っぽく
st.markdown("""
    <style>
    .stChatMessage { background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.sidebar.title("🎙 AI Streamer Engine")

# 入力項目
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("更新間隔（秒）", 10, 60, 25)

# セッション管理
if "chat_queue" not in st.session_state: st.session_state.chat_queue = Queue()
if "conn_status" not in st.session_state: st.session_state.conn_status = "🔴 未接続"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "last_topic" not in st.session_state: st.session_state.last_topic = "" # 記憶用
if "ai_mood" not in st.session_state: st.session_state.ai_mood = "普通"

# --- 2. Twitch監視 (変更なし・安定版) ---
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
            st.session_state.conn_status = "🟢 同期中"
            while True:
                data = sock.recv(2048).decode("utf-8")
                if not data: break
                if data.startswith("PING"):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                elif "PRIVMSG" in data:
                    parts = data.split("!")
                    user = parts[0][1:] if len(parts) > 0 else "unknown"
                    msg = data.split(f"#{channel} :", 1)[1].strip() if f"#{channel} :" in data else ""
                    if msg: queue.put({"user": user, "text": msg})
        except:
            st.session_state.conn_status = "🔴 再接続中..."
            time.sleep(5)

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN and "thread_started" not in st.session_state:
    t = threading.Thread(target=twitch_listener, args=(TW_CHANNEL, TW_ACCESS_TOKEN, st.session_state.chat_queue), daemon=True)
    t.start()
    st.session_state.thread_started = True

# --- 3. AI思考エンジン (記憶と情緒を強化) ---
def generate_ai_talk():
    collected = []
    while not st.session_state.chat_queue.empty():
        collected.append(st.session_state.chat_queue.get())
    
    # 前回の話題を記憶として保持
    memory_context = f"前回の話題: {st.session_state.last_topic}" if st.session_state.last_topic else "これが最初の話題です。"
    
    if collected:
        summary = "\n".join([f"- {m['user']}: {m['text']}" for m in collected])
        prompt = f"""あなたは知性的で皮肉屋なAI。現在の気分: {st.session_state.ai_mood}。
        {memory_context}
        
        【指示】
        1. 視聴者の声「{collected[0]['user']}: {collected[0]['text']}」を拾いつつ、前回の話題からの繋がりを意識して。
        2. 全体のコメント「{summary}」を分析し、現代社会の矛盾としてバッサリ斬って。
        3. 150文字程度の生放送の喋り。セリフは「」内のみ。
        """
    else:
        prompt = f"""チャットが静かです。現在の気分: {st.session_state.ai_mood}。
        {memory_context}
        視聴者の無関心を皮肉りつつ、独自に「不条理な社会ニュース」を1つ選んで、
        あなたの哲学を150文字程度で語って。「」内のみ。"""

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={ST_GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in [
            "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_DANGEROUS_CONTENT"
        ]]
    }
    
    try:
        res = requests.post(url, json=payload, timeout=15)
        text = res.json()['candidates'][0]['content']['parts'][0]['text']
        # 話題を記憶（次の回で利用）
        st.session_state.last_topic = text[:50] + "..." 
        return text
    except Exception as e:
        return f"（データが詰まったわ。APIを確認して。{str(e)[:20]}）"

# --- 4. 実行ロジック ---
def run_ai_cycle():
    talk = generate_ai_talk()
    if talk:
        st.session_state.chat_history.append(talk)
        st.session_state.last_talk = talk.replace("「", "").replace("」", "").replace("\n", " ")
        # 気分をランダムに変化させる演出
        import random
        st.session_state.ai_mood = random.choice(["絶好調", "やや不機嫌", "哲学的", "少しデレ"])

# --- 5. メイン UI ---
st.title("🤖 AI Streamer Pro v2.6")

# ステータス表示
c1, c2, c3 = st.columns(3)
c1.metric("Twitch同期", st.session_state.conn_status)
c2.metric("待機中コメント", st.session_state.chat_queue.qsize())
c3.metric("AIの機嫌", st.session_state.ai_mood)

st.divider()

# 履歴表示（最新を上へ）
for m in reversed(st.session_state.chat_history[-10:]): # 直近10件のみ
    st.chat_message("assistant", avatar="🤖").write(m)

# 操作系
if st.button("🎙 次の話題へ（手動/自動）", type="primary", on_click=run_ai_cycle):
    pass

# --- 6. JS (音声・更新) ---
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
