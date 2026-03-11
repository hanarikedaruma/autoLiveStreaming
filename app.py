import streamlit as st
import requests
import json
from supabase import create_client, Client

# --- 1. 設定サイドバー ---
st.sidebar.title("🔐 Twitch & AI Settings")

# Gemini設定
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()

# Twitch設定 (最新のToken Generatorに対応)
TW_CHANNEL = st.sidebar.text_input("2. Twitch Channel ID (ユーザー名)", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password", placeholder="先ほどの緑色の文字").strip()
TW_CLIENT_ID = st.sidebar.text_input("4. Client ID", placeholder="一番下の英数字").strip()

# Supabase設定
ST_SUPABASE_URL = st.sidebar.text_input("5. Supabase URL").strip()
ST_SUPABASE_KEY = st.sidebar.text_input("6. Supabase Anon Key", type="password").strip()

if all([ST_GEMINI_KEY, TW_CHANNEL, TW_ACCESS_TOKEN, TW_CLIENT_ID, ST_SUPABASE_URL, ST_SUPABASE_KEY]):
    
    # 【最新のHelix APIでチャットを取得する関数】
    def get_twitch_chat_helix():
        try:
            # まずユーザーIDを取得
            user_url = f"https://api.twitch.tv/helix/users?login={TW_CHANNEL}"
            headers = {
                "Client-ID": TW_CLIENT_ID,
                "Authorization": f"Bearer {TW_ACCESS_TOKEN}"
            }
            user_res = requests.get(user_url, headers=headers, timeout=5).json()
            broadcaster_id = user_res['data'][0]['id']

            # 最新のチャットを取得
            chat_url = f"https://api.twitch.tv/helix/chat/messages?broadcaster_id={broadcaster_id}"
            chat_res = requests.get(chat_url, headers=headers, timeout=5).json()
            
            messages = [m['text'] for m in chat_res.get('data', [])]
            return messages[-3:] if messages else ["(チャットがまだありません)"]
        except Exception as e:
            return [f"(接続エラー: API設定を確認してください)"]

    # 【Gemini API実行】
    def call_gemini_api(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return None

    # --- UI ---
    st.title("🤖 最新Twitch API対応：AI配信者")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 最新チャットに反応する"):
        with st.spinner("チャットを読み込み中..."):
            comments = get_twitch_chat_helix()
            comment_summary = " | ".join(comments)
            st.info(f"取得したチャット: {comment_summary}")

            prompt = f"あなたは皮肉屋なAI。視聴者のコメント「{comment_summary}」に対して一言毒舌を「」内で言って。"
            speech = call_gemini_api(prompt)
            
            if speech:
                st.session_state.chat_history.append(speech)
                # 音声再生
                clean_speech = speech.replace("「","").replace("」","")
                st.components.v1.html(f"""
                    <script>
                    var msg = new SpeechSynthesisUtterance("{clean_speech}");
                    msg.lang = "ja-JP";
                    window.speechSynthesis.speak(msg);
                    </script>
                """, height=0)

    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant").write(m)
else:
    st.warning("サイドバーの項目をすべて入力してください。")
