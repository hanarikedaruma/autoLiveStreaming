import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import random
import time
import json

# --- 1. 設定 ---
st.sidebar.title("Settings")
ST_GEMINI_KEY = st.sidebar.text_input("Gemini API Key", type="password")
ST_SUPABASE_URL = st.sidebar.text_input("Supabase URL")
ST_SUPABASE_KEY = st.sidebar.text_input("Supabase Anon Key", type="password")

if ST_GEMINI_KEY and ST_SUPABASE_URL and ST_SUPABASE_KEY:
    try:
        genai.configure(api_key=ST_GEMINI_KEY)
        supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)
    except Exception as e:
        st.error(f"初期化エラー: {e}")

    # --- 2. 話題作成 ---
    def process_topic_generation(comments, random_seed):
        # モデル名を 'models/gemini-1.5-flash' に修正
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        prompt = f"コメント:{comments}、要素:{random_seed}から面白い配信の話題を1つ作り、JSON形式で返せ。{{'topic': '内容', 'tags': '単語'}}"
        
        try:
            response = model.generate_content(prompt)
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            topic_data = json.loads(raw_text)
            
            embed = genai.embed_content(model="models/text-embedding-004", content=topic_data['topic'])['embedding']

            res = supabase.rpc('match_topics', {
                'query_embedding': embed,
                'match_threshold': 0.8,
                'match_count': 1
            }).execute()

            if res.data:
                return None
            
            supabase.table("topics").insert({"content": topic_data['topic'], "embedding": embed}).execute()
            return topic_data
        except Exception as e:
            st.error(f"話題生成中にエラーが発生しました: {e}")
            return None

    # --- 3. 配信AI ---
    def generate_speech(topic_text):
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        char_prompt = f"あなたは皮肉屋なAI配信者。話題: {topic_text} に対するセリフを「」内に書いてください。"
        response = model.generate_content(char_prompt)
        return response.text

    # --- 4. UI ---
    st.title("📱 AI Autonomous Streamer")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("配信サイクルを開始"):
        seeds = ["2026年の流行", "AIの逆襲", "iPhone開発の限界"]
        topic = process_topic_generation("テスト中", random.choice(seeds))
        
        if topic:
            speech = generate_speech(topic['topic'])
            st.session_state.chat_history.append(speech)
            
            clean_speech = speech.split("「")[-1].split("」")[0]
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{clean_speech}");
                msg.lang = "ja-JP";
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)
        else:
            st.info("話題が重複したか、エラーによりスキップされました。")

    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant").write(m)
else:
    st.warning("サイドバーで全てのAPIキーを入力してください。")
