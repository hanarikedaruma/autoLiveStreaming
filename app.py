import streamlit as st
import requests
import json
import socket
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🔐 Twitch Connection")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    
    def fetch_chat():
        try:
            sock = socket.socket()
            sock.settimeout(10.0)
            sock.connect(("irc.chat.twitch.tv", 6667))
            
            token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
            sock.send(f"PASS {token}\r\n".encode("utf-8"))
            sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
            
            # ログイン処理が完了するまで（End of MOTD = 376が出るまで）ループ
            while True:
                initial_data = sock.recv(2048).decode("utf-8")
                if "376" in initial_data or "End of /NAMES list" in initial_data:
                    break
            
            # ここからが本当のチャット待機
            st.toast("ログイン完了。今すぐTwitchで発言してください！")
            
            start_wait = time.time()
            while time.time() - start_wait < 10: # 10秒間粘る
                try:
                    data = sock.recv(2048).decode("utf-8")
                    if "PING" in data:
                        sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                    
                    if "PRIVMSG" in data:
                        # メッセージ部分だけを抽出
                        msg = data.split(" :", 1)[1].strip() if " :" in data else data
                        # もし「#」が含まれるIRC形式ならさらに絞り込む
                        if f"#{TW_CHANNEL} :" in data:
                            msg = data.split(f"#{TW_CHANNEL} :", 1)[1].strip()
                        
                        sock.close()
                        return msg
                except socket.timeout:
                    continue
            
            sock.close()
            return None
        except Exception as e:
            st.error(f"エラー: {e}")
            return None

    def call_gemini_api(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return "AIが反応できませんでした。"

    # --- UI ---
    st.title("🎙 執念のTwitch反応モード")
    st.info("ボタンを押して『ログイン完了』と出たら、すぐにTwitchでコメントしてください。")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 チャットを待ち伏せする"):
        with st.spinner("Twitchサーバーに潜入中..."):
            comment = fetch_chat()
            
            if comment:
                st.success(f"✅ 捕まえたコメント: {comment}")
                prompt = f"皮肉屋なAIとして、視聴者のコメント「{comment}」に短く鋭い皮肉を「」内で一言。"
            else:
                st.warning("⚠️ 誰もいませんでした...")
                prompt = "誰もいない静かなチャットルームで、人間の気まぐれさを皮肉る一言を「」内で言って。"

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
