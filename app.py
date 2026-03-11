import streamlit as st
import socket
import threading
import google.generativeai as genai
import time
import random

st.set_page_config(
    page_title="AI Twitch Streamer",
    page_icon="🎙",
    layout="wide"
)

# -------------------------
# セッション
# -------------------------

if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

if "ai_message" not in st.session_state:
    st.session_state.ai_message = "AIはまだ話していません"

if "connected" not in st.session_state:
    st.session_state.connected = False

# -------------------------
# サイドバー UI
# -------------------------

st.sidebar.title("⚙️ AI Streamer Setup")

BOT_NAME = st.sidebar.text_input("Bot Username")
CHANNEL = st.sidebar.text_input("Channel Name")
TOKEN = st.sidebar.text_input("OAuth Token", type="password")
GEMINI_KEY = st.sidebar.text_input("Gemini API Key", type="password")

st.sidebar.markdown("---")

if st.session_state.connected:
    st.sidebar.success("🟢 Twitch Connected")
else:
    st.sidebar.warning("🔴 Not Connected")

# -------------------------
# Gemini設定
# -------------------------

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

def generate_ai_talk(topic):

    prompt = f"""
あなたは皮肉屋なAI配信者です。
短く面白くコメントしてください。

話題:
{topic}

出力は「」の中のみ。
"""

    try:
        res = model.generate_content(prompt)
        return res.text
    except:
        return "「AIの脳がラグってる…」"

# -------------------------
# Twitch Chat Listener
# -------------------------

def twitch_listener():

    sock = socket.socket()
    sock.connect(("irc.chat.twitch.tv", 6667))

    token = TOKEN
    if not token.startswith("oauth:"):
        token = "oauth:" + token

    sock.send(f"PASS {token}\r\n".encode())
    sock.send(f"NICK {BOT_NAME}\r\n".encode())
    sock.send(f"JOIN #{CHANNEL}\r\n".encode())

    st.session_state.connected = True

    while True:

        resp = sock.recv(2048).decode("utf-8")

        if resp.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode())

        if "PRIVMSG" in resp:

            user = resp.split("!")[0][1:]
            msg = resp.split("PRIVMSG")[1].split(":",1)[1]

            st.session_state.chat_log.append({
                "user": user,
                "text": msg
            })

            ai = generate_ai_talk(msg)

            st.session_state.ai_message = ai

# -------------------------
# ランダム雑談
# -------------------------

def idle_talk():

    topics = [
        "ゲーム実況",
        "インターネット文化",
        "猫",
        "深夜テンション",
        "人類の未来",
        "AIの仕事"
    ]

    while True:

        time.sleep(45)

        if len(st.session_state.chat_log) == 0:

            topic = random.choice(topics)

            ai = generate_ai_talk(topic)

            st.session_state.ai_message = ai

# -------------------------
# メインUI
# -------------------------

st.title("🎙 AI Twitch Streamer")

col1, col2 = st.columns([2,1])

# -------------------------
# 左：チャット
# -------------------------

with col1:

    st.subheader("💬 Twitch Chat")

    chat_box = st.container(height=400)

    with chat_box:

        for chat in st.session_state.chat_log[-20:]:

            st.markdown(
                f"""
                **{chat['user']}**
                : {chat['text']}
                """
            )

# -------------------------
# 右：AI
# -------------------------

with col2:

    st.subheader("🤖 AI Comment")

    st.markdown(
        f"""
        ## {st.session_state.ai_message}
        """
    )

# -------------------------
# 配信開始
# -------------------------

st.markdown("---")

if st.button("🚀 配信開始"):

    threading.Thread(target=twitch_listener, daemon=True).start()
    threading.Thread(target=idle_talk, daemon=True).start()

    st.success("AI配信スタート")

# -------------------------
# 自動更新
# -------------------------

st.components.v1.html(
"""
<script>
setTimeout(function(){
    window.location.reload();
}, 5000);
</script>
""",
height=0
)