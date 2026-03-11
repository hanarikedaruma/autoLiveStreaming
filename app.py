import streamlit as st
import socket
import threading
import google.generativeai as genai
import time
import random

st.set_page_config(page_title="AI Twitch Streamer", layout="wide")

# --------------------------
# セッション状態
# --------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "ai_message" not in st.session_state:
    st.session_state.ai_message = "AI待機中..."

if "connected" not in st.session_state:
    st.session_state.connected = False

if "bot_running" not in st.session_state:
    st.session_state.bot_running = False


# --------------------------
# UI
# --------------------------

st.title("🎙 AI Twitch Streamer")

col1, col2 = st.columns([2,1])

with col1:
    st.subheader("💬 Twitch Chat")

    chat_container = st.container(height=400)

    with chat_container:
        for m in st.session_state.messages[-20:]:
            st.write(f"**{m['user']}** : {m['text']}")

with col2:
    st.subheader("🤖 AI Talk")

    st.markdown(
        f"""
        ### {st.session_state.ai_message}
        """
    )

# --------------------------
# サイドバー
# --------------------------

st.sidebar.title("⚙ Setup")

bot_name = st.sidebar.text_input("Bot Username")
channel = st.sidebar.text_input("Channel")
token = st.sidebar.text_input("OAuth Token", type="password")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password")

if st.session_state.connected:
    st.sidebar.success("🟢 Connected")
else:
    st.sidebar.warning("🔴 Disconnected")


# --------------------------
# Gemini設定
# --------------------------

if gemini_key:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")


def ai_talk(topic):

    prompt = f"""
あなたは毒舌なAI配信者です。
短くコメントしてください。

話題:
{topic}

出力は「」の中だけ。
"""

    try:
        r = model.generate_content(prompt)
        return r.text
    except:
        return "「AIの脳が停止中…」"


# --------------------------
# Twitch BOT
# --------------------------

def twitch_bot():

    try:

        sock = socket.socket()
        sock.connect(("irc.chat.twitch.tv", 6667))

        # oauth自動付与
        t = token.strip()
        if not t.startswith("oauth:"):
            t = "oauth:" + t

        sock.send(f"PASS {t}\r\n".encode())
        sock.send(f"NICK {bot_name}\r\n".encode())
        sock.send(f"JOIN #{channel}\r\n".encode())

        st.session_state.connected = True

        while True:

            resp = sock.recv(2048).decode("utf-8")

            if resp.startswith("PING"):
                sock.send("PONG :tmi.twitch.tv\r\n".encode())

            if "PRIVMSG" in resp:

                user = resp.split("!")[0][1:]
                msg = resp.split("PRIVMSG")[1].split(":",1)[1]

                st.session_state.messages.append({
                    "user": user,
                    "text": msg
                })

                ai = ai_talk(msg)

                st.session_state.ai_message = ai

    except Exception as e:

        st.session_state.connected = False
        print("ERROR:", e)


# --------------------------
# 雑談AI
# --------------------------

def idle_ai():

    topics = [
        "ゲーム実況",
        "猫",
        "インターネット文化",
        "深夜テンション",
        "人間社会",
        "AIの未来"
    ]

    while True:

        time.sleep(60)

        if len(st.session_state.messages) == 0:

            topic = random.choice(topics)

            st.session_state.ai_message = ai_talk(topic)


# --------------------------
# 起動
# --------------------------

if st.sidebar.button("🚀 Start AI Streamer"):

    if not st.session_state.bot_running:

        st.session_state.bot_running = True

        threading.Thread(target=twitch_bot, daemon=True).start()
        threading.Thread(target=idle_ai, daemon=True).start()

        st.sidebar.success("AI Bot Started")


# --------------------------
# 自動更新
# --------------------------

st.components.v1.html(
"""
<script>
setTimeout(function(){
window.location.reload();
},4000);
</script>
""",
height=0
)