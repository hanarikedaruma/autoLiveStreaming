import streamlit as st
import socket
import threading
import time
import requests
from queue import Queue

# --- 1. 設定サイドバー ---
st.sidebar.title("🎙 AI Streamer Live Engine")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("AIの反応間隔（秒）", 15, 60, 30)

# --- 2. グローバルなデータ置き場 (Queue) ---
# アプリがリロードされても消えないように session_state で管理
if "chat_queue" not in st.session_state:
    st.session_state.chat_queue = Queue()
if "conn_status" not in st.session_state:
    st.session_state.conn_status = "🔴 未接続"

# --- 3. 常時同期スレッド（Twitch Listener） ---
def twitch_listener(channel, token, queue):
    """裏側でずっとTwitchに接続し、コメントをQueueに溜め続ける"""
    while True:
        try:
            sock = socket.socket()
            sock.settimeout(5.0)
            sock.connect(("irc.chat.twitch.tv", 6667))
            
            auth_token = token if token.startswith("oauth:") else f"oauth:{token}"
            sock.send(f"PASS {auth_token}\r\n".encode("utf-8"))
            sock.send(f"NICK {channel}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{channel}\r\n".encode("utf-8"))
            sock.send("CAP REQ :twitch.tv/tags twitch.tv/commands\r\n".encode("utf-8"))
            
            st.session_state.conn_status = "🟢 常時同期中"
            
            while True:
                try:
                    data = sock.recv(2048).decode("utf-8")
                    if not data: break
                    
                    if data.startswith("PING"):
                        sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                    elif "PRIVMSG" in data:
                        # コメント解析
                        user = data.split("!")[0][1:]
                        msg = data.split(f"#{channel} :", 1)[1].strip()
                        # キューに保存
                        queue.put({"user": user, "text": msg})
                except socket.timeout:
                    continue
        except:
            st.session_state.conn_status = "🔴 再接続待機中..."
            time.sleep(5)

# スレッドの起動管理
if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    if "thread_started" not in st.session_state:
        # スレッドに渡すための引数を準備
        t = threading.Thread(
            target=twitch_listener, 
            args=(TW_CHANNEL, TW_ACCESS_TOKEN, st.session_state.chat_queue),
            daemon=True
        )
        t.start()
        st.session_state.thread_started = True

# --- 4. AI思考 & 表示ロジック ---
def get_talk_from_ai():
    # キューに溜まっているコメントをすべて回収
    collected = []
    while not st.session_state.chat_queue.empty():
        collected.append(st.session_state.chat_queue.get())
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
    
    if collected:
        # 最新の数件を要約してプロンプトへ
        chat_summary = " | ".join([f"{c['user']}: {c['text']}" for c in collected[-5:]])
        prompt = f"皮肉屋なAI配信者として、視聴者たちのコメント「{chat_summary}」をまとめて受け止めつつ、そこから毒舌を交えた150文字程度のフリートークを展開して。「」内のみ。"
    else:
        prompt = "チャットが静かなので、皮肉屋なAI配信者として人間の飽きっぽさを煽りつつ、自発的に150文字程度の毒舌トークを広げて。「」内のみ。"

    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

# --- 5. UI ---
st.title("📺 常時同期型AI配信システム")
st.metric("接続状態", st.session_state.conn_status)
st.write(f"未処理のコメント: {st.session_state.chat_queue.qsize()} 件")

# 自動更新 JavaScript
st.components.v1.html(f"""
    <script>
    setTimeout(function(){{
        window.parent.document.querySelector('button[kind="primary"]').click();
    }}, {refresh_rate * 1000});
    </script>
""", height=0)

if st.button("🎙 更新 / 思考実行", type="primary"):
    talk = get_talk_from_ai()
    if talk:
        st.chat_message("assistant", avatar="🤖").write(talk)
        # 音声再生
        st.components.v1.html(f"""
            <script>
            var msg = new SpeechSynthesisUtterance("{talk.replace('「','').replace('」','')}");
            msg.lang = "ja-JP";
            msg.pitch = 0.8;
            window.speechSynthesis.speak(msg);
            </script>
        """, height=0)

# 履歴表示（省略）
