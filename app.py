import streamlit as st
import requests
import socket
import time
import threading

# --- 1. 設定サイドバー ---
st.sidebar.title("🎙 AI Streamer Console")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("AIの反応間隔（秒）", 15, 60, 30)

# セッション状態の初期化
if "twitch_buffer" not in st.session_state:
    st.session_state.twitch_buffer = []
if "conn_status" not in st.session_state:
    st.session_state.conn_status = "🔴 未接続"

# --- 2. Twitch監視スレッド (常時接続) ---
def twitch_monitor():
    """Twitchサーバーとの接続を維持し、メッセージを監視する"""
    while True: # 切断されても再接続を繰り返す
        try:
            st.session_state.conn_status = "🟡 接続試行中..."
            sock = socket.socket()
            sock.settimeout(5.0)
            sock.connect(("irc.chat.twitch.tv", 6667))
            
            token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
            sock.send(f"PASS {token}\r\n".encode("utf-8"))
            sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
            
            st.session_state.conn_status = "🟢 接続済み"
            
            while True:
                try:
                    data = sock.recv(2048).decode("utf-8")
                    if not data: break # 切断された場合
                    
                    if data.startswith("PING"):
                        sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                    elif "PRIVMSG" in data:
                        user = data.split("!")[0][1:]
                        msg = data.split(f"#{TW_CHANNEL} :", 1)[1].strip()
                        st.session_state.twitch_buffer.append(f"{user}: {msg}")
                except socket.timeout:
                    continue # タイムアウトは無視して続行
        except:
            st.session_state.conn_status = "🔴 切断（再試行中）"
            time.sleep(5)

# 接続開始
if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    if "thread_active" not in st.session_state:
        st.session_state.thread_active = True
        threading.Thread(target=twitch_monitor, daemon=True).start()

    # 【トーク生成】
    def generate_ai_talk():
        comments = st.session_state.twitch_buffer.copy()
        st.session_state.twitch_buffer = [] # バッファをリセット
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        
        if comments:
            comment_text = " | ".join(comments)
            prompt = f"皮肉屋なAI配信者として、最新のコメント「{comment_text}」を受け止めつつ、そこから現代社会の歪みについて150文字程度で鋭く独り言を言って。「」内のセリフのみ。"
        else:
            prompt = "チャットが静かなので、皮肉屋なAI配信者として人間の飽きっぽさを嘆きつつ、今思いついた『腹立たしい日常の話題』について150文字程度で毒舌を吐いて。「」内のセリフのみ。"

        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return None

    # --- 3. メイン画面 ---
    st.title("🤖 AI配信システム：ライブ稼働中")

    # 🚀 ステータス表示エリア
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Twitch接続状態", st.session_state.conn_status)
    with col2:
        st.metric("待機中のコメント", f"{len(st.session_state.twitch_buffer)} 件")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 自動更新 JS
    st.components.v1.html(f"""
        <script>
        setTimeout(function(){{
            window.parent.document.querySelector('button[kind="primary"]').click();
        }}, {refresh_rate * 1000});
        </script>
    """, height=0)

    if st.button("🎙 更新 / 思考実行", type="primary"):
        talk = generate_ai_talk()
        if talk:
            st.session_state.chat_history.append(talk)
            clean_talk = talk.replace("「","").replace("」","")
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{clean_talk}");
                msg.lang = "ja-JP";
                msg.pitch = 0.8;
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)

    # 履歴表示
    st.divider()
    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant", avatar="🤖").write(m)
else:
    st.warning("サイドバーにAPIキーとチャンネルIDを入力してください。")
