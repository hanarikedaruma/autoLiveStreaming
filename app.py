import streamlit as st
import requests
import json
from supabase import create_client, Client

# --- 1. 設定サイドバー ---
st.sidebar.title("🔐 Twitch & AI Settings")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch Channel ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
TW_CLIENT_ID = st.sidebar.text_input("4. Client ID").strip()
ST_SUPABASE_URL = st.sidebar.text_input("5. Supabase URL").strip()
ST_SUPABASE_KEY = st.sidebar.text_input("6. Supabase Anon Key", type="password").strip()

if all([ST_GEMINI_KEY, TW_CHANNEL, TW_ACCESS_TOKEN, TW_CLIENT_ID, ST_SUPABASE_URL, ST_SUPABASE_KEY]):
    
    def get_twitch_chat_helix():
        try:
            headers = {"Client-ID": TW_CLIENT_ID, "Authorization": f"Bearer {TW_ACCESS_TOKEN}"}
            # ユーザーID取得
            user_res = requests.get(f"https://api.twitch.tv/helix/users?login={TW_CHANNEL}", headers=headers, timeout=5).json()
            broadcaster_id = user_res['data'][0]['id']
            # 最新メッセージ取得
            chat_res = requests.get(f"https://api.twitch.tv/helix/chat/messages?broadcaster_id={broadcaster_id}", headers=headers, timeout=5).json()
            
            messages = [m['text'] for m in chat_res.get('data', [])]
            return messages if messages else None
        except:
            return None

    def call_gemini_api(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return None

    # --- UI ---
    st.title("🎙 実況中：AI配信者システム")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 最新の空気を読んで発言"):
        with st.spinner("Twitchを覗き見中..."):
            comments = get_twitch_chat_helix()
            
            if comments:
                comment_text = " | ".join(comments[-3:])
                st.success(f"拾ったコメント: {comment_text}")
                prompt = f"皮肉屋なAIとして、視聴者のコメント「{comment_text}」に鋭いツッコミを一言「」内で言って。"
            else:
                st.warning("チャットが空っぽです。")
                prompt = "チャットに誰もいなくて暇をしている皮肉屋なAIとして、人間の気まぐれさについて一言「」内でぼやいて。"

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
else:
    st.info("サイドバーに情報を入力してください。")
