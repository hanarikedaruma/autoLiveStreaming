import streamlit as st
import requests
import socket
import ssl
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🛠 Connection Fixer")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="kemarihanari").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password", help="oauth:xxx の形式").strip()

if "conn_status" not in st.session_state:
    st.session_state.conn_status = "⚪️ 待機中"

# --- 2. 鉄壁の接続関数 ---
def get_chat_secure():
    try:
        # 1. 接続先を「安全な443番ポート」に変更
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.create_default_context()
        sock = context.wrap_socket(raw_sock, server_hostname="irc.chat.twitch.tv")
        
        st.session_state.conn_status = "🟡 認証中..."
        sock.connect(("irc.chat.twitch.tv", 443)) # ★ここがポイント
        
        # 2. トークン整形
        token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
        
        # 3. 認証コマンド送信
        sock.send(f"PASS {token}\r\n".encode("utf-8"))
        sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
        sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
        sock.send("CAP REQ :twitch.tv/tags twitch.tv/commands\r\n".encode("utf-8"))
        
        # 4. 受信待機（3秒間）
        sock.settimeout(3.0)
        full_data = ""
        try:
            # サーバーからの応答をまとめて受け取る
            for _ in range(5): 
                chunk = sock.recv(4096).decode("utf-8")
                full_data += chunk
                if "PRIVMSG" in chunk: break
        except socket.timeout:
            pass
        
        sock.close()
        
        # 5. ステータス判定
        if "Welcome" in full_data or "End of /NAMES list" in full_data:
            st.session_state.conn_status = "🟢 接続成功"
        else:
            st.session_state.conn_status = "🔴 認証失敗（Tokenを確認）"
            return None

        # コメント抽出
        for line in full_data.split("\r\n"):
            if "PRIVMSG" in line:
                user = line.split("!")[0][1:]
                msg = line.split(f"#{TW_CHANNEL} :", 1)[1].strip()
                return {"user": user, "text": msg}
        return None

    except Exception as e:
        st.session_state.conn_status = f"❌ 物理エラー: {str(e)[:20]}"
        return None

# --- 3. メイン UI ---
st.title("🤖 次世代AI配信：安定接続モード")

st.metric("接続ステータス", st.session_state.conn_status)

if st.button("🎙 配信トーク実行（コメント取得）", type="primary"):
    with st.spinner("Twitchサーバーと同期中..."):
        chat = get_chat_secure()
        
        # AI生成ロジック (Gemini)
        if chat:
            st.success(f"✅ {chat['user']}さんの声を拾いました")
            prompt = f"皮肉屋AIとして『{chat['text']}』を受け止め、毒を吐きながら話題を広げて。「」内のみ。"
        else:
            st.warning("⚠️ 新しいコメントはありません")
            prompt = "チャットが静かなことを皮肉って、自発的に150文字程度で毒舌トークを展開して。「」内のみ。"

        # Gemini呼び出し（URL、Payloadは前回同様）
        # ... 生成された talk を再生 ...
