import streamlit as st
import requests
import json
import socket
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🔍 Twitch Live Connector")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    
    def listen_to_twitch():
        try:
            sock = socket.socket()
            sock.settimeout(10.0) # ★10秒間、コメントを待ち続ける設定
            sock.connect(("irc.chat.twitch.tv", 6667))
            
            token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
            sock.send(f"PASS {token}\r\n".encode("utf-8"))
            sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
            
            start_time = time.time()
            st.toast("Twitchに接続しました。コメントを待っています...")
            
            while True:
                # 10秒経過したらタイムアウト
                if time.time() - start_time > 10:
                    break
                    
                data = sock.recv(2048).decode("utf-8")
                
                # サーバーからの生存確認(PING)に答える（これをしないと切断されます）
                if data.startswith("PING"):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                
                # コメント(PRIVMSG)を見つけたら即座に返す
                if "PRIVMSG" in data:
                    msg = data.split(f"#{TW_CHANNEL} :", 1)[-1].strip()
                    sock.close()
                    return msg
            
            sock.close()
            return None
        except Exception as e:
            return None

    def call_gemini_api(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return "（AIが考え込んでいます）"

    # --- UI ---
    st.title("🤖 リアルタイム反応：AI配信者")
    st.info("下のボタンを押してから10秒以内に、Twitchでコメントを打ってみてください！")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 チャット受信を開始（10秒間待機）"):
        with st.spinner("コメント待機中... Twitchで何か打ってください！"):
            comment = listen_to_twitch()
            
            if comment:
                st.success(f"✅ 受信: {comment}")
                prompt = f"皮肉屋なAIとして、視聴者のコメント「{comment}」に鋭く一言答えて。短く！"
            else:
                st.warning("⚠️ 時間切れです。誰も話してくれませんでした。")
                prompt = "誰も話しかけてくれないので、人間の愛想のなさを皮肉る一言を「」内で言って。"

            speech = call_gemini_api(prompt)
            st.session_state.chat_history.append(speech)
            
            # 音声再生
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{speech.replace('「','').replace('」','')}");
                msg.lang = "ja-JP";
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)

    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant", avatar="🤖").write(m)
