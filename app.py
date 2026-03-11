import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import random
import json

# --- 1. 設定サイドバー ---
st.sidebar.title("🛠 API Settings")
ST_GEMINI_KEY = st.sidebar.text_input("Gemini API Key", type="password")
ST_SUPABASE_URL = st.sidebar.text_input("Supabase URL")
ST_SUPABASE_KEY = st.sidebar.text_input("Supabase Anon Key", type="password")

if ST_GEMINI_KEY and ST_SUPABASE_URL and ST_SUPABASE_KEY:
    try:
        genai.configure(api_key=ST_GEMINI_KEY)
        supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)
    except Exception as e:
        st.error(f"初期化エラー: {e}")

    # 話題作成
    def process_topic_generation(comments, random_seed):
        # 404回避の最終手段：バージョン番号(002)を直接指定
        model_name = 'gemini-1.5-flash-002'
        
        try:
            model = genai.GenerativeModel(model_name)
            prompt = f"コメント:{comments}、要素:{random_seed}から配信の話題を1つ作り、JSONで返せ。{{'topic': '内容', 'tags': '単語'}}"
            
            response = model.generate_content(prompt)
            if not response.text: return None

            text = response.text.replace("```json", "").replace("```", "").strip()
            topic_data = json.loads(text)
            
            # Embedding（ここも 404 が出る場合は text-embedding-004 に変更済み）
            embed_resp = genai.embed_content(
                model="models/text-embedding-004", 
                content=topic_data['topic']
            )
            embed = embed_resp['embedding']

            res = supabase.rpc('match_topics', {
                'query_embedding': embed,
                'match_threshold': 0.8,
                'match_count': 1
            }).execute()

            if res.data and len(res.data) > 0: return None 
            
            supabase.table("topics").insert({"content": topic_data['topic'], "embedding": embed}).execute()
            return topic_data
        except Exception as e:
            st.error(f"話題生成エラー詳細: {str(e)}")
            return None

    # 配信者回答生成
    def generate_streaming_speech(topic_text):
        try:
            # こちらもバージョン固定
            model = genai.GenerativeModel('gemini-1.5-flash-002')
            char_prompt = f"あなたは皮肉屋なAI配信者。話題: {topic_text} に対する一言を「」内に書いて。"
            response = model.generate_content(char_prompt)
            return response.text
        except Exception as e:
            return f"（エラー... {str(e)[:30]}）"

    # --- UI ---
    st.title("🤖 自律型AI配信システム")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 新しい話題で配信！"):
        seeds = ["AIの進化", "無駄の美学", "未来の食卓"]
        topic = process_topic_generation("テスト", random.choice(seeds))
        
        if topic:
            st.success(f"話題: {topic['topic']}")
            speech = generate_streaming_speech(topic['topic'])
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
