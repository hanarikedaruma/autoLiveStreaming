import streamlit as st
import socket
import threading

st.sidebar.title("🎙 AI Streamer Console")
TW_CHANNEL = st.sidebar.text_input("Twitch ID").lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("Access Token", type="password")

if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

def twitch_listener():
    sock = socket.socket()
    sock.connect(("irc.chat.twitch.tv", 6667))

    token = TW_ACCESS_TOKEN
    if not token.startswith("oauth:"):
        token = "oauth:" + token

    sock.send(f"PASS {token}\r\n".encode())
    sock.send(f"NICK {TW_CHANNEL}\r\n".encode())
    sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode())

    while True:
        resp = sock.recv(2048).decode("utf-8")

        if resp.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode())

        if "PRIVMSG" in resp:
            parts = resp.split("!")
            user = parts[0][1:]

            msg = resp.split("PRIVMSG")[1].split(":",1)[1].strip()

            st.session_state.chat_log.append({
                "user": user,
                "text": msg
            })

st.title("📺 AI実況システム")

if st.button("チャット接続開始"):

    thread = threading.Thread(target=twitch_listener)
    thread.daemon = True
    thread.start()

    st.success("チャット監視開始")

for chat in st.session_state.chat_log[-10:]:
    st.write(f"🎤 {chat['user']} : {chat['text']}")