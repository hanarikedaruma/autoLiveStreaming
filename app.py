import streamlit as st
import requests
import json
from supabase import create_client, Client
import random

# --- 1. 設定サイドバー ---
st.sidebar.title("🛠 API Settings")
ST_GEMINI_KEY = st.sidebar.text_input("Gemini API Key", type="password")
ST_SUPABASE_URL = st.sidebar.text_input("Supabase URL")
ST_SUPABASE_KEY = st.sidebar.text_input("Supabase Anon Key", type="password")

if ST_GEMINI_KEY and ST_SUPABASE_URL and ST_SUPABASE_KEY:
    supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)

    # 【利用可能なモデルを自動取得する関数】
    def get_available_model():
        # あなたのAPIキーで使えるモデルの一覧を取得
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={ST_GEMINI_KEY}"
        try:
            res = requests.get(url).json()
            models = [m['name'].split('/')[-1] for m in res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            # 優先順位: 1.5-flash -> 2.0-flash -> その他
            # 2.0を飛ばして、1.5-flash を最優先にする
for priority in ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-2.0-flash']:
	if priority in models: return priority
		return models[0] if models else "gemini-1.5-flash"
        except:
            return "gemini-1.5-flash"

    # 【API実行：自動選択されたモデルを使用】
    def call_gemini_api(prompt):
        target_model = get_available_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={ST_GEMINI_KEY}"
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            st.error(f"モデル {target_model} でエラー: {response.status_code}")
            st.json(response.json())
            return None

    # --- UI & 実行 ---
    st.title("🤖 究極の自律型AI配信者")
    st.info(f"現在の有効モデル: {get_available_model()}")

    if st.button("🎙 配信を開始"):
        # 話題生成
        topic_raw = call_gemini_api("配信の話題を1つ、JSON形式で返せ。{'topic': '内容'}")
        if topic_raw:
            try:
                clean_text = topic_raw.replace("```json", "").replace("```", "").strip()
                topic_data = json.loads(clean_text)
                st.success(f"話題: {topic_data['topic']}")
                
                # セリフ生成
                speech = call_gemini_api(f"話題: {topic_data['topic']} について皮肉を一言。")
                if speech:
                    st.chat_message("assistant").write(speech)
                    # 音声再生
                    st.components.v1.html(f"""
                        <script>
                        var msg = new SpeechSynthesisUtterance("{speech.replace('「','').replace('」','')}");
                        msg.lang = "ja-JP";
                        window.speechSynthesis.speak(msg);
                        </script>
                    """, height=0)
            except:
                st.error("JSON解析に失敗しました。もう一度試してください。")

else:
    st.warning("サイドバーでAPIキーを入力してください。")
