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
        # API初期化
        genai.configure(api_key=ST_GEMINI_KEY)
        supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)
    except Exception as e:
        st.error(f"初期化エラー: {e}")

    # 【話題作成 & 重複チェック】
    def process_topic_generation(comments, random_seed):
        # 修正：プレフィックスありのフルパス指定に変更
        # これで 404 が出る場合は 'gemini-1.5-flash' (プレフィックスなし) も試す価値あり
        model_name = 'models/gemini-1.5-flash'
        
        try:
            model = genai.GenerativeModel(model_name)
            
            prompt = f"コメント:{comments}、要素:{random_seed}から面白い配信の話題を1つ作り、JSON形式で返せ。{{'topic': '内容', 'tags': '単語'}}"
            
            # 生成実行
            response = model.generate_content(prompt)
            
            # 返答が空でないかチェック
            if not response.text:
                return None

            # JSON部分を抽出
            text = response.text.replace("```json", "").replace("```", "").strip()
            topic_data = json.loads(text)
            
            # ベクトル化（Embeddingもモデル名をフルパス指定）
            embed_resp = genai.embed_content(
                model="models/text-embedding-004", 
                content=topic_data['topic']
            )
            embed = embed_resp['embedding']

            # Supabase判定 (RPC呼び出し)
            res = supabase.rpc('match_topics', {
                'query_embedding': embed,
                'match_threshold': 0.8,
                'match_count': 1
            }).execute()

            if res.data and len(res.data) > 0:
                return None 
            
            # 履歴保存
            supabase.table("topics").insert({
                "content": topic_data['topic'], 
                "embedding": embed
            }).execute()
            
            return topic_data
        except Exception as e:
            st.error(f"話題生成エラー詳細: {str(e)}")
            return None

    # 【配信者回答生成】
    def generate_streaming_speech(topic_text):
        try:
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            char_prompt = f"あなたは皮肉屋なAI配信者。話題: {topic_text} に対する一言を「」内に書いて。"
            response = model.generate_content(char_prompt)
            return response.text
        except Exception as e:
            return f"（エラーよ... {str(e)[:40]}）"

    # --- 3. メインUI ---
    st.title("🤖 自律型AI配信システム")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 新しい話題で配信！"):
        seeds = ["2026年の労働観", "AIが笑う日", "猫に学ぶ生存戦略"]
        topic = process_topic_generation("テスト中", random.choice(seeds))
        
        if topic:
            st.success(f"話題決定: {topic['topic']}")
            speech = generate_streaming_speech(topic['topic'])
            st.session_state.chat_history.append(speech)
            
            # iPhone音声再生用JavaScript
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
    st.info("左側のサイドバーで設定を完了させてください。")
