import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import random
import time
import json

# --- 1. 設定サイドバー ---
st.sidebar.title("🛠 API Settings")
ST_GEMINI_KEY = st.sidebar.text_input("Gemini API Key", type="password")
ST_SUPABASE_URL = st.sidebar.text_input("Supabase URL")
ST_SUPABASE_KEY = st.sidebar.text_input("Supabase Anon Key", type="password")

# --- 2. メイン処理ロジック ---
if ST_GEMINI_KEY and ST_SUPABASE_URL and ST_SUPABASE_KEY:
    try:
        genai.configure(api_key=ST_GEMINI_KEY)
        supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)
    except Exception as e:
        st.error(f"初期化エラー: {e}")

    # 話題作成 & 重複チェック
    def process_topic_generation(comments, random_seed):
        # モデル名を -latest に修正して404エラーを回避
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        
        prompt = f"""
        あなたは話題作成AIです。
        コメント: {comments}
        ランダム要素: {random_seed}
        これらから配信の話題を1つ作り、以下のJSON形式でのみ返せ。
        {{"topic": "内容", "tags": "単語"}}
        """
        
        try:
            response = model.generate_content(prompt)
            # JSON部分を安全に抽出
            text = response.text.replace("```json", "").replace("```", "").strip()
            topic_data = json.loads(text)
            
            # ベクトル化
            embed_resp = genai.embed_content(
                model="models/text-embedding-004", 
                content=topic_data['topic']
            )
            embed = embed_resp['embedding']

            # Supabaseで類似度判定
            res = supabase.rpc('match_topics', {
                'query_embedding': embed,
                'match_threshold': 0.8,
                'match_count': 1
            }).execute()

            if res.data and len(res.data) > 0:
                return None # 類似話題あり
            
            # 履歴に保存
            supabase.table("topics").insert({
                "content": topic_data['topic'], 
                "embedding": embed
            }).execute()
            
            return topic_data
        except Exception as e:
            st.error(f"話題生成エラー: {e}")
            return None

    # 配信者回答生成
    def generate_streaming_speech(topic_text):
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        char_prompt = f"""
        あなたは皮肉屋で博識なAI配信者。
        話題: {topic_text}
        この話題に対して、視聴者がニヤリとするようなコメントを「」の中に書いてください。
        セリフ以外は出力しないでください。
        """
        try:
            response = model.generate_content(char_prompt)
            return response.text
        except Exception as e:
            st.error(f"発言生成エラー: {e}")
            return "（通信エラーかしらね...）"

    # --- 3. アプリケーションUI ---
    st.title("🤖 自律型AI配信システム")
    st.caption("話題作成から発言までAIが自動で行います")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 次の話題で配信を開始"):
        seeds = ["2026年の最先端技術", "昭和の謎ルール", "美味しい猫缶の選び方", "iPhone開発の限界"]
        topic = process_topic_generation("視聴者からの挨拶", random.choice(seeds))
        
        if topic:
            st.success(f"新話題: {topic['topic']}")
            speech = generate_streaming_speech(topic['topic'])
            st.session_state.chat_history.append(speech)
            
            # ブラウザでの音声読み上げ（JavaScript）
            clean_speech = speech.split("「")[-1].split("」")[0]
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{clean_speech}");
                msg.lang = "ja-JP";
                msg.rate = 1.0;
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)
        else:
            st.info("似た話題が過去にあったため、スキップされました。もう一度押してください。")

    # 履歴表示
    st.divider()
    for m in reversed(st.session_state.chat_history):
        with st.chat_message("assistant"):
            st.write(m)
else:
    st.warning("サイドバーにAPIキー等を入力してください。")
