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

    # 【APIを直接叩く関数：v1 エンドポイントを使用】
    def call_gemini_api(prompt):
        # バージョンを v1beta から v1 に変更し、404 を物理的に回避
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                # エラー詳細を表示
                st.error(f"APIエラー: {response.status_code}")
                st.json(response.json())
                return None
        except Exception as e:
            st.error(f"通信エラー: {e}")
            return None

    # 話題作成
    def process_topic_generation(comments, random_seed):
        prompt = f"配信の話題を1つ作り、JSONで返せ。{{'topic': '内容', 'tags': '単語'}}"
        
        res_text = call_gemini_api(prompt)
        if not res_text: return None
        
        try:
            clean_text = res_text.replace("```json", "").replace("```", "").strip()
            topic_data = json.loads(clean_text)
            
            # Embeddingも v1 エンドポイントへ
            embed_url = f"https://generativelanguage.googleapis.com/v1/models/text-embedding-004:embedContent?key={ST_GEMINI_KEY}"
            embed_payload = {"content": {"parts": [{"text": topic_data['topic']}]}}
            embed_res = requests.post(embed_url, headers={'Content-Type': 'application/json'}, json=embed_payload)
            embed = embed_res.json()['embedding']['values']

            # Supabase判定
            res = supabase.rpc('match_topics', {
                'query_embedding': embed,
                'match_threshold': 0.8,
                'match_count': 1
            }).execute()

            if res.data and len(res.data) > 0: return None 
            
            supabase.table("topics").insert({"content": topic_data['topic'], "embedding": embed}).execute()
            return topic_data
        except Exception as e:
            st.error(f"解析エラー: {e}")
            return None

    # --- UI ---
    st.title("🤖 自律型AI配信者 (v1-REST)")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 配信を開始"):
        topic = process_topic_generation("テスト", "AIの未来")
        if topic:
            st.success(f"話題: {topic['topic']}")
            speech = call_gemini_api(f"話題: {topic['topic']} について皮肉を言え。")
            if speech:
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
        st.chat_message("assistant").write(m)
