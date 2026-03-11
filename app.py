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

    # 【話題作成 & 重複チェック】
    def process_topic_generation(comments, random_seed):
        # 404対策：SDKにモデル選択を任せるためプレフィックスを調整
        try:
            # モデル名の指定を最も堅牢な形式に変更
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"コメント:{comments}、要素:{random_seed}から面白い配信の話題を1つ作り、以下のJSON形式でのみ返せ。{{'topic': '内容', 'tags': '単語'}}"
            
            # 安全な生成実行
            response = model.generate_content(prompt)
            
            if not response.text:
                st.error("AIからの返答が空でした。")
                return None

            text = response.text.replace("```json", "").replace("```", "").strip()
            topic_data = json.loads(text)
            
            # ベクトル化（ここも404が出やすいので注意）
            embed_resp = genai.embed_content(
                model="models/text-embedding-004", 
                content=topic_data['topic']
            )
            embed = embed_resp['embedding']

            # Supabase判定
            res = supabase.rpc('match_topics', {
                'query_embedding': embed,
                'match_threshold': 0.8,
                'match_count': 1
            }).execute()

            if res.data and len(res.data) > 0:
                return None 
            
            supabase.table("topics").insert({
                "content": topic_data['topic'], 
                "embedding": embed
            }).execute()
            
            return topic_data
        except Exception as e:
            # エラー内容を詳しく表示
            st.error(f"詳細エラー報告: {str(e)}")
            if "404" in str(e):
                st.info("💡 対策: APIキーが『Google AI Studio』で作成された最新のものか再確認してください。")
            return None

    # 【配信者回答生成】
    def generate_streaming_speech(topic_text):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            char_prompt = f"あなたは皮肉屋なAI配信者。話題: {topic_text} に対する一言を「」内に書いて。"
            response = model.generate_content(char_prompt)
            return response.text
        except Exception as e:
            return f"（エラーね... {str(e)[:50]}）"

    # --- 3. UI ---
    st.title("🤖 自律型AI配信システム")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 次の話題を生成"):
        seeds = ["AIと人間の境界", "レトロブームの謎", "効率化の罠"]
        topic = process_topic_generation("こんにちは", random.choice(seeds))
        
        if topic:
            st.success(f"話題: {topic['topic']}")
            speech = generate_streaming_speech(topic['topic'])
            st.session_state.chat_history.append(speech)
            
            # 音声再生
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
