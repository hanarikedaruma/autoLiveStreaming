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
        # APIの初期化
        genai.configure(api_key=ST_GEMINI_KEY)
        supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)
    except Exception as e:
        st.error(f"初期化エラー: {e}")

    # 【話題作成 & 重複チェック】
    def process_topic_generation(comments, random_seed):
        # 404エラー回避のため、最も標準的なモデル名 'gemini-1.5-flash' を使用
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            あなたは話題作成AIです。
            コメント: {comments}
            ランダム要素: {random_seed}
            これらから配信の話題を1つ作り、以下のJSON形式でのみ返せ。余計な解説は不要。
            {{"topic": "内容", "tags": "単語"}}
            """
            
            response = model.generate_content(prompt)
            # JSON部分を安全に抽出
            text = response.text.replace("```json", "").replace("```", "").strip()
            topic_data = json.loads(text)
            
            # ベクトル化（Embedding）
            embed_resp = genai.embed_content(
                model="models/text-embedding-004", 
                content=topic_data['topic']
            )
            embed = embed_resp['embedding']

            # Supabaseで類似度判定（RPC呼び出し）
            res = supabase.rpc('match_topics', {
                'query_embedding': embed,
                'match_threshold': 0.8,
                'match_count': 1
            }).execute()

            if res.data and len(res.data) > 0:
                return None # 似た話題がある場合はやり直し
            
            # 話題を履歴に保存
            supabase.table("topics").insert({
                "content": topic_data['topic'], 
                "embedding": embed
            }).execute()
            
            return topic_data
        except Exception as e:
            st.error(f"話題生成エラー: {e}")
            return None

    # 【配信者回答生成】
    def generate_streaming_speech(topic_text):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            char_prompt = f"""
            あなたは皮肉屋で博識なAI配信者。
            話題: {topic_text}
            この話題に対して、視聴者がニヤリとするような皮肉まじりのコメントを「」の中に書いて。
            セリフ以外は一切出力しないでください。
            """
            response = model.generate_content(char_prompt)
            return response.text
        except Exception as e:
            st.error(f"発言生成エラー: {e}")
            return "（通信エラーかしらね...。興ざめだわ。）"

    # --- 3. アプリケーションUI ---
    st.title("🤖 自律型AI配信者：稼働中")
    st.caption("話題作成・重複チェック・発言生成をすべてAIが自動実行します。")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # メイン実行ボタン
    if st.button("🎙 次の話題を生成して配信"):
        seeds = ["2026年のAIの地位", "レトロゲームの魅力", "理想的な休日の過ごし方", "人間の非合理性"]
        # コメントは現状固定（将来的に拡張可能）
        topic = process_topic_generation("こんにちは！", random.choice(seeds))
        
        if topic:
            st.success(f"【話題】: {topic['topic']}")
            speech = generate_streaming_speech(topic['topic'])
            st.session_state.chat_history.append(speech)
            
            # ブラウザ音声読み上げ（iPhone対応JavaScript）
            clean_speech = speech.split("「")[-1].split("」")[0]
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{clean_speech}");
                msg.lang = "ja-JP";
                msg.rate = 1.1; // 少し早口で皮肉っぽく
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)
        else:
            st.info("過去の話題と似ていたためスキップしました。もう一度ボタンを押してください。")

    # ログ表示
    st.divider()
    for m in reversed(st.session_state.chat_history):
        with st.chat_message("assistant"):
            st.write(m)

else:
    st.warning("左側のサイドバーを開き、GeminiとSupabaseの設定を入力してください。")
