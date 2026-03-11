import streamlit as st
import requests
import json
import socket # チャットサーバーに直接繋ぐためのライブラリ
from supabase import create_client, Client

# --- 1. 設定サイドバー ---
st.sidebar.title("🔐 Twitch 強制接続モード")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID (小文字)", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
ST_SUPABASE_URL = st.sidebar.text_input("4. Supabase URL").strip()
ST_SUPABASE_KEY = st.sidebar.text_input("5. Supabase Anon Key", type="password").strip()

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    
    # 【IRC方式：配信中じゃなくてもコメントを引っこ抜く関数】
    def get_twitch_chat_irc():
        try:
            sock = socket.socket()
            sock.settimeout(2.0)
            sock.connect(("irc.chat.twitch.tv", 6667))
            
            # 認証（Access Tokenの頭に oauth: を自動で付けます）
            token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
            sock.send(f"PASS {token}\r\n".encode("utf-8"))
            sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
            
            # データを一気に読み込む
            data = sock.recv(2048).decode("utf-8")
            sock.close()
            
            messages = []
            for line in data.split("\r\n"):
                if "PRIVMSG" in line:
                    # メッセージ本体を抽出
                    msg = line.split(f"#{TW_CHANNEL} :", 1)[-1]
                    messages.append(msg)
            
            return messages if messages else None
        except Exception as e:
            st.sidebar.error(f"接続失敗: {e}")
            return None

    def call_gemini_api(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return None

    # --- UI ---
    st.title("🎙 AI配信者：チャット強制取得モード")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 チャットを読み取って発言"):
        with st.spinner("Twitchサーバーに潜入中..."):
            comments = get_twitch_chat_irc()
            
            if comments:
                comment_text = " / ".join(comments[-3:])
                st.success(f"取得成功: {comment_text}")
                prompt = f"皮肉屋なAIとして、視聴者のコメント「{comment_text}」に鋭いツッコミを「」内で一言。短く！"
            else:
                st.warning("やはりチャットが見つかりません。")
                prompt = "チャットが静まり返っていることに呆れている皮肉屋なAIとして、一言「」内でぼやいて。"

            speech = call_gemini_api(prompt)
            
            if speech:
                st.session_state.chat_history.append(speech)
                clean_speech = speech.replace("「","").replace("」","")
                st.components.v1.html(f"""
                    <script>
                    var msg = new SpeechSynthesisUtterance("{clean_speech}");
                    msg.lang = "ja-JP";
                    window.speechSynthesis.speak(msg);
                    </script>
                """, height=0)

    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant", avatar="🤖").write(m)
