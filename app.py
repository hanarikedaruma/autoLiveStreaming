import streamlit as st
import requests
import json
from supabase import create_client, Client
import random
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🛠 API Settings")
# キーを貼り付けた際の余計なスペースを自動で削除する処理を追加
ST_GEMINI_KEY = st.sidebar.text_input("Gemini API Key", type="password").strip()
ST_SUPABASE_URL = st.sidebar.text_input("Supabase URL").strip()
ST_SUPABASE_KEY = st.sidebar.text_input("Supabase Anon Key", type="password").strip()

if ST_GEMINI_KEY and ST_SUPABASE_URL and ST_SUPABASE_KEY:
    try:
        supabase: Client = create_client(ST_SUPABASE_URL, ST_SUPABASE_KEY)
    except Exception as e:
        st.sidebar.error(f"Supabase接続エラー: {e}")

    # 【API実行：404/429を回避するためのREST API通信】
    def call_gemini_api(prompt):
        # 404対策：通常版が認識されないプロジェクトでも通りやすい 'gemini-1.5-flash-8b' を使用
        target_model = "gemini-1.5-flash-8b"
        
        # エンドポイントは最も汎用的な v1beta を使用
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={ST_GEMINI_KEY}"
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 404:
                # それでも 404 が出る場合は、さらに別のモデル名 (gemini-1.5-flash) を試すロジック
                st.warning("モデルが見つからないため、別モデルで再試行中...")
                url_alt = url.replace("gemini-1.5-flash-8b", "gemini-1.5-flash")
                response_alt = requests.post(url_alt, headers=headers, json=payload)
                if response_alt.status_code == 200:
                    return response_alt.json()['candidates'][0]['content']['parts'][0]['text']
                else:
                    st.error(f"404エラー: プロジェクトでモデルが無効です。{response_alt.text}")
                    return None
            elif response.status_code == 429:
                st.error("リクエスト制限（429）です。1分待ってから再開してください。")
                return None
            else:
                st.error(f"APIエラー ({response.status_code}): {response.text}")
                return None
        except Exception as e:
            st.error(f"通信失敗: {e}")
            return None

    # --- 配信 UI ---
    st.title("🤖 完結版：自律型AI配信システム")
    st.caption("モデル: gemini-1.5-flash-8b (404回避モード)")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("🎙 配信（話題生成）を開始"):
        # 1. 話題生成
        topic_prompt = "配信の面白い話題を1つ、JSON形式で返せ。形式: {'topic': '内容'}"
        topic_raw = call_gemini_api(topic_prompt)
        
        if topic_raw:
            try:
                # JSON部分を安全に抽出
                clean_text = topic_raw.replace("```json", "").replace("```", "").strip()
                topic_data = json.loads(clean_text)
                st.success(f"話題決定: {topic_data['topic']}")
                
                # 2. セリフ生成
                speech_prompt = f"話題「{topic_data['topic']}」について、皮肉屋なAI配信者として「」内で一言答えて。セリフ以外は不要。"
                speech = call_gemini_api(speech_prompt)
                
                if speech:
                    st.session_state.chat_history.append(speech)
                    # ブラウザ音声読み上げ
                    clean_speech = speech.replace("「","").replace("」","")
                    st.components.v1.html(f"""
                        <script>
                        var msg = new SpeechSynthesisUtterance("{clean_speech}");
                        msg.lang = "ja-JP";
                        window.speechSynthesis.speak(msg);
                        </script>
                    """, height=0)
            except Exception as e:
                st.warning("生成された内容を解析できませんでした。もう一度ボタンを押してください。")

    # 履歴表示
    st.divider()
    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant").write(m)

else:
    st.info("サイドバーにAPIキーを入力してください。")
