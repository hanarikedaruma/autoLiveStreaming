import streamlit as st
import requests
import json
import socket
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🔍 Twitch 接続デバッグ")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID (小文字)", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    
    def get_twitch_chat_debug():
        try:
            sock = socket.socket()
            sock.settimeout(5.0) # 少し長めに待つ
            sock.connect(("irc.chat.twitch.tv", 6667))
            
            # トークンの整形
            token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
            
            # ログインコマンド送信
            sock.send(f"PASS {token}\r\n".encode("utf-8"))
            sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
            
            # サーバーからの応答を2回に分けて受け取る（1回目はログイン完了、2回目がチャット）
            response = ""
            for _ in range(2):
                chunk = sock.recv(2048).decode("utf-8")
                response += chunk
                if "PRIVMSG" in chunk: break
                time.sleep(0.5)
            
            sock.close()

            # デバッグ情報の表示（開発者用）
            with st.expander("通信ログを確認"):
                st.code(response)

            if "Login authentication failed" in response:
                return "AUTH_ERROR"
            
            messages = []
            for line in response.split("\r\n"):
                if "PRIVMSG" in line:
                    msg = line.split(f"#{TW_CHANNEL} :", 1)[-1]
                    messages.append(msg)
            
            return messages if messages else None
        except Exception as e:
            st.error(f"接続エラー: {e}")
            return None

    def call_gemini_api(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return "（AIが沈黙しています）"

    # --- UI ---
    st.title("🤖 最終デバッグ：AI配信システム")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 チャットを取得して反応"):
        res = get_twitch_chat_debug()
        
        if res == "AUTH_ERROR":
            st.error("❌ トークンが無効です。再度取得し直してください。")
            prompt = "認証に失敗してキレている皮肉屋なAIとして一言。"
        elif res:
            comment_text = " / ".join(res[-3:])
            st.success(f"✅ 取得成功: {comment_text}")
            prompt = f"皮肉屋なAIとして、コメント「{comment_text}」に鋭く一言答えて。"
        else:
            st.warning("⚠️ チャットが見つかりません。")
            prompt = "チャットが静かすぎることに絶望している皮肉屋なAIとして一言。"

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
