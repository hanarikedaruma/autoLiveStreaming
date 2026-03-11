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

    # 【APIを直接叩く関数】
    def call_gemini_api(prompt):
        # SDKを使わず、直接URLを指定して404を回避
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            st.error(f"APIエラー: {response.status_code} - {response.text}")
            return None

    # 話題作成
    def process_topic_generation(comments, random_seed):
        prompt = f"コメント:{comments}、要素:{random_seed}から配信の話題を1つ作り、以下の形式で返せ。{{'topic': '内容', 'tags': '単語'}}"
        
        res_text = call_gemini_api(prompt)
        if not res_text: return None
        
        try:
            # JSON部分を抽出
            clean_text = res_text.replace("```json", "").replace("```", "").strip()
            topic_data = json.loads(clean_text)
            
            # ベクトル化（EmbeddingもAPI直叩き）
            embed_url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={ST_GEMINI_KEY}"
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

    # --- 配信 UI ---
    st.title("🤖 自律型AI配信者 (REST版)")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 次の話題で配信！"):
        seeds = ["2026年のトレンド", "AIの逆説", "朝食の重要性"]
        topic = process_topic_generation("テスト", random.choice(seeds))
        
        if topic:
            st.success(f"話題: {topic['topic']}")
            speech_prompt = f"あなたは皮肉屋なAI配信者。話題: {topic['topic']} に対するセリフを「」内に書いて。"
            speech = call_gemini_api(speech_prompt)
            
            if speech:
                st.session_state.chat_history.append(speech)
                clean_speech = speech.split("「")[-1].split("」")[0]
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
    st.info("サイドバーにキーを入力してください。")
