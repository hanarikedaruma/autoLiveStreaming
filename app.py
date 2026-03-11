import streamlit as st
import requests
import json
import socket
from supabase import create_client, Client
import random
import time

# --- 1. 設定サイドバー（すべての情報を外から入力） ---
st.sidebar.title("🔐 API & Stream Settings")

# Gemini設定
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()

# Twitch設定
TW_CHANNEL = st.sidebar.text_input("2. Twitch Channel ID", placeholder="your_id").strip().lower()
TW_TOKEN = st.sidebar.text_input("3. Twitch OAuth Token", type="password", placeholder="oauth:xxxx").strip()

# Supabase設定
ST_SUPABASE_URL = st.sidebar.text_input("4. Supabase URL").strip()
ST_SUPABASE_KEY = st.sidebar.text_input("5. Supabase Anon Key", type="password").strip()

# すべての入力が揃っているかチェック
if all([ST_GEMINI_KEY, TW_CHANNEL, TW_TOKEN, ST_SUPABASE_URL, ST_SUPABASE_KEY]):
    
    # Supabase初期化
    try:
        supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)
    except:
        st.sidebar.error("Supabase接続失敗")

    # 【Twitchコメント取得関数】
    def get_twitch_chat():
        try:
            sock = socket.socket()
            sock.settimeout(3.0) # 接続待ち時間
            sock.connect(("irc.chat.twitch.tv", 6667))
            
            # 認証送信
            sock.send(f"PASS {TW_TOKEN}\r\n".encode("utf-8"))
            sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
            
            data = sock.recv(2048).decode("utf-8")
            sock.close()
            
            # PRIVMSG行からメッセージを抽出
            msgs = []
            for line in data.split("\r\n"):
                if "PRIVMSG" in line:
                    parts = line.split(":", 2)
                    if len(parts) > 2:
                        msgs.append(parts[2])
            
            return msgs[-3:] if msgs else ["(現在コメントはありません)"]
        except Exception as e:
            return [f"(接続エラー: {str(e)[:20]})"]

    # 【Gemini API実行関数】
    def call_gemini_api(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, timeout=15)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except:
            return None

    # --- メイン UI ---
    st.title("🤖 自律型AI配信：Twitch連携")
    st.caption(f"現在接続中: {TW_CHANNEL}")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 コメントを拾って反応する"):
        with st.spinner("Twitchチャットをスキャン中..."):
            comments = get_twitch_chat()
            comment_summary = " | ".join(comments)
            st.info(f"拾ったコメント: {comment_summary}")

            # AIへの指示（プロンプト）
            prompt = f"""
            あなたは皮肉屋なAI配信者。
            Twitchの最新コメント: 「{comment_summary}」
            これに対して、毒舌を交えつつ配信の「一言」を「」内で言ってください。
            コメントが「接続エラー」や「ありません」の場合は、勝手に人間の愚かさについてぼやいて。
            セリフ以外は不要。
            """
            
            speech = call_gemini_api(prompt)
            
            if speech:
                st.session_state.chat_history.append(speech)
                # ブラウザ音声再生
                clean_speech = speech.replace("「","").replace("」","")
                st.components.v1.html(f"""
                    <script>
                    var msg = new SpeechSynthesisUtterance("{clean_speech}");
                    msg.lang = "ja-JP";
                    msg.pitch = 0.9;
                    window.speechSynthesis.speak(msg);
                    </script>
                """, height=0)

    # 履歴表示
    st.divider()
    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant", avatar="🤖").write(m)

else:
    st.warning("サイドバーの 1〜5 すべての項目を入力してください。")
    st.info("💡 Twitch OAuth Tokenは https://twitchapps.com/tmi/ で取得した oauth:xxxx の形式で入力してください。")
