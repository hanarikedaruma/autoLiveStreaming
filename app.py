import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import random
import time
import json

# --- 1. 設定（StreamlitのSecretsに保存することを推奨） ---
# iPhoneでテストする際は、直接入力するか、サイドバーで設定可能にします
ST_GEMINI_KEY = st.sidebar.text_input("Gemini API Key", type="password")
ST_SUPABASE_URL = st.sidebar.text_input("Supabase URL")
ST_SUPABASE_KEY = st.sidebar.text_input("Supabase Anon Key", type="password")

if ST_GEMINI_KEY and ST_SUPABASE_URL and ST_SUPABASE_KEY:
    genai.configure(api_key=ST_GEMINI_KEY)
    supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)

    # --- 2. 話題作成 & 類似度チェックロジック ---
    def process_topic_generation(comments, random_seed):
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 話題生成
        prompt = f"コメント:{comments}、要素:{random_seed}から面白い配信の話題を1つ作り、以下のJSON形式で返せ。{{'topic': '内容', 'tags': '単語'}}"
        response = model.generate_content(prompt)
        # JSON部分のみ抽出（簡易実装）
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        topic_data = json.loads(raw_text)

        # ベクトル化
        embed = genai.embed_content(model="models/text-embedding-004", content=topic_data['topic'])['embedding']

        # 類似度判定（SupabaseのRPCを呼び出し）
        res = supabase.rpc('match_topics', {
            'query_embedding': embed,
            'match_threshold': 0.8,
            'match_count': 1
        }).execute()

        if res.data:
            return None # 重複あり
        
        # 履歴に保存
        supabase.table("topics").insert({"content": topic_data['topic'], "embedding": embed}).execute()
        return topic_data

    # --- 3. 配信AIロジック ---
    def generate_speech(topic_text):
        model = genai.GenerativeModel('gemini-1.5-flash')
        char_prompt = f"""
        あなたは皮肉屋なAI配信者。一人称「私」。語尾「〜ね」「〜かしら」。
        話題: {topic_text}
        感情(Positive/Flat/Negative)と、回答形式(Episode/Phrase/Word)を決め、
        「」の中にセリフだけを出力してください。
        """
        response = model.generate_content(char_prompt)
        return response.text

    # --- 4. UIレイアウト（Streamlit） ---
    st.title("📱 AI Autonomous Streamer")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("配信サイクルを開始"):
        # 話題生成
        seeds = ["2026年の流行", "AIの逆襲", "最高の猫缶", "iPhoneだけで開発する苦労"]
        topic = process_topic_generation("テストコメント", random.choice(seeds))
        
        if topic:
            # セリフ生成
            speech = generate_speech(topic['topic'])
            st.session_state.chat_history.append(speech)
            
            # --- 5. iPhoneのブラウザで声を出すJavaScript ---
            # セリフ部分だけを抽出（「」の中身）
            clean_speech = speech.split("「")[-1].split("」")[0]
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{clean_speech}");
                msg.lang = "ja-JP";
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)
        else:
            st.warning("話題が被ったので再生成してください。")

    # ログ表示
    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant").write(m)

else:
    st.info("サイドバーにAPIキーを入力してください。")
