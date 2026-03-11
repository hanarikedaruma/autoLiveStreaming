import streamlit as st
import requests
import json
from supabase import create_client, Client
import random
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🚀 Next-Gen AI Settings")
ST_GEMINI_KEY = st.sidebar.text_input("Gemini API Key", type="password").strip()
ST_SUPABASE_URL = st.sidebar.text_input("Supabase URL").strip()
ST_SUPABASE_KEY = st.sidebar.text_input("Supabase Anon Key", type="password").strip()

if ST_GEMINI_KEY and ST_SUPABASE_URL and ST_SUPABASE_KEY:
    try:
        supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)
    except Exception as e:
        st.sidebar.error("Supabase接続エラー")

    # 【API実行：Gemini 2.5 Flash を最優先に指定】
    def call_gemini_api(prompt):
        # 最新の 2.5 Flash モデルを指定。もし 404 が出る場合は 1.5 に自動フォールバック
        model_list = [
            "gemini-2.5-flash", 
            "gemini-2.0-flash", 
            "gemini-1.5-flash"
        ]
        
        for model_name in model_list:
            # 最新エンドポイント v1 を優先使用
            url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={ST_GEMINI_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 1.0}
            }
            
            try:
                response = requests.post(url, json=payload, timeout=15)
                if response.status_code == 200:
                    res_json = response.json()
                    return res_json['candidates'][0]['content']['parts'][0]['text']
                elif response.status_code == 404:
                    continue # 次のモデルを試す
                elif response.status_code == 429:
                    st.error("2.5 Flashの利用制限中です。1分待機してください。")
                    return None
            except:
                continue
        
        st.error("利用可能なGeminiモデルが見つかりません。APIキーを確認してください。")
        return None

    # --- メイン UI ---
    st.title("⚡️ 自律型AI配信：Gemini 2.5 Edition")
    st.caption("最新のFlashモデルによる高速話題生成モード")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 最新モデルで配信を開始"):
        # 1. 話題生成（2.5 Flash はJSON指示への理解が非常に高い）
        topic_prompt = "配信の斬新な話題を1つ、JSONのみで返せ。{'topic': '内容'}"
        topic_raw = call_gemini_api(topic_prompt)
        
        if topic_raw:
            try:
                # クリーンアップ処理
                clean_text = topic_raw.replace("```json", "").replace("```", "").strip()
                topic_data = json.loads(clean_text)
                st.success(f"【話題】: {topic_data['topic']}")
                
                # 2. セリフ生成
                speech_prompt = f"話題「{topic_data['topic']}」について、博識で毒舌なAI配信者として「」内で一言。セリフ以外は不要。"
                speech = call_gemini_api(speech_prompt)
                
                if speech:
                    st.session_state.chat_history.append(speech)
                    # ブラウザ音声再生
                    clean_speech = speech.replace("「","").replace("」","")
                    st.components.v1.html(f"""
                        <script>
                        var msg = new SpeechSynthesisUtterance("{clean_speech}");
                        msg.lang = "ja-JP";
                        msg.pitch = 1.2; // 少し高めの声で
                        window.speechSynthesis.speak(msg);
                        </script>
                    """, height=0)
            except:
                st.warning("生成データの解析に失敗。もう一度お試しください。")

    # 履歴
    st.divider()
    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant").write(m)
else:
    st.info("サイドバーでAPI設定を完了してください。")
