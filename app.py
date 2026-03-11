import streamlit as st
import requests
import json
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🚀 AI Streamer Pro")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="kemarihanari").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("更新間隔（秒）", 15, 60, 30)

# --- 2. Twitch API：コメント取得 (新方式) ---
def get_twitch_chat_api():
    """IRCを使わず、API経由で最新のチャットログを取得する"""
    try:
        # まず自分のチャンネルのID（数字）を取得
        token = TW_ACCESS_TOKEN.replace("oauth:", "")
        headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": "gp762nuuoqcoxypju8c569th9wz7q5", # 一般的なクライアントID
        }
        
        # ユーザーID取得
        u_res = requests.get(f"https://api.twitch.tv/helix/users?login={TW_CHANNEL}", headers=headers)
        user_id = u_res.json()['data'][0]['id']
        
        # チャット設定取得（接続確認用）
        c_res = requests.get(f"https://api.twitch.tv/helix/chat/settings?broadcaster_id={user_id}", headers=headers)
        
        if c_res.status_code == 200:
            st.session_state.conn_status = "🟢 接続成功 (API)"
        else:
            st.session_state.conn_status = f"🔴 認証エラー: {c_res.status_code}"
            return None

        # ※本来はWebSocketが必要ですが、簡易的に「最近のメッセージ」を模索
        # IRCがダメな場合、ここでのエラー詳細を st.write で出すのが解決への近道です。
        return None 
    except Exception as e:
        st.session_state.conn_status = f"🔴 接続不可: {str(e)[:30]}"
        return None

# --- 3. AI思考 & 配信ロジック ---
def run_stream_cycle():
    # 実際にはIRCが最も早いため、前述の「CAP REQ」付きIRCを
    # 確実に通すためのデバッグ情報を出します
    st.write("### 🔍 接続診断")
    if not TW_ACCESS_TOKEN.startswith("oauth:"):
        st.error("アクセストークンは 'oauth:' から始まっていますか？")
    
    # 接続テスト
    try:
        import socket
        s = socket.create_connection(("irc.chat.twitch.tv", 6667), timeout=5)
        st.success("✅ Twitchサーバーへの通信経路は生きています。")
        s.close()
    except:
        st.error("❌ 通信経路が遮断されています。Wi-Fiを変えるかVPNを切ってください。")

# --- UI ---
st.title("🤖 AI配信エンジン：稼働診断")
st.metric("接続ステータス", st.session_state.get("conn_status", "🔴 未起動"))

if st.button("🎙 配信開始 / 接続テスト"):
    run_stream_cycle()

# 履歴表示（省略）
