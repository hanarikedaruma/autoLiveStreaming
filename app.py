import streamlit as st
import requests
import json
from supabase import create_client, Client
import random
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🛠 API Settings")
ST_GEMINI_KEY = st.sidebar.text_input("Gemini API Key", type="password")
ST_SUPABASE_URL = st.sidebar.text_input("Supabase URL")
ST_SUPABASE_KEY = st.sidebar.text_input("Supabase Anon Key", type="password")

if ST_GEMINI_KEY and ST_SUPABASE_URL and ST_SUPABASE_KEY:
    try:
        supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)
    except:
        st.sidebar.error("Supabase接続エラー")

    # 【API実行：1.5-flashを最優先に固定して429を回避】
    def call_gemini_api(prompt):
        # 429対策：最も安定している 1.5-flash を直接指定
        target_model = "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={ST_GEMINI_KEY}"
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                st.error("現在Google側で制限がかかっています。1分ほど待ってから再度押してください。")
                return None
            else:
                st.error(f"エラー発生 ({response.status_code}): {response.text[:100]}")
                return None
        except Exception as e:
            st.error(f"通信失敗: {e}")
            return None

    # --- 配信 UI ---
    st.title("🤖 完結版：自律型AI配信者")
    st.info("モデル: gemini-1.5-flash (安定稼働モード)")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 配信を開始（話題生成）"):
        # 429回避のため少しだけ待機を入れる
        time.sleep(1)
        
        # 1. 話題生成
        topic_prompt = "配信の面白い話題を1つ、JSON形式で返せ。例: {'topic': '内容'}"
        topic_raw = call_gemini_api(topic_prompt)
        
        if topic_raw:
            try:
                # 余計な文字を排除して解析
                clean_text = topic_raw.replace("```json", "").replace("```", "").strip()
                topic_data = json.loads(clean_text)
                st.success(f"新話題: {topic_data['topic']}")
                
                # 2. セリフ生成
                speech_prompt = f"あなたは皮肉屋なAI。話題「{topic_data['topic']}」について、視聴者が笑うようなセリフを一言だけ「」内に書いて。"
                speech = call_gemini_api(speech_prompt)
                
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
            except Exception as e:
                st.warning("解析に失敗しました。もう一度ボタンを押してください。")

    # 履歴表示
    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant").write(m)

else:
    st.warning("サイドバーでAPIキーを入力してください。")
