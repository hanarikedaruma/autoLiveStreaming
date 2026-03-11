import streamlit as st
import requests
import socket
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🎙 AI Streamer Stable")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("AIの反応間隔（秒）", 15, 60, 30)

# セッション管理
if "chat_log" not in st.session_state:
    st.session_state.chat_log = [] # AIのセリフ履歴
if "conn_status" not in st.session_state:
    st.session_state.conn_status = "🔴 未起動"

# --- 2. Twitch接続・取得コア関数 ---
def get_twitch_messages_stable():
    """更新のたびにサーバーへ繋ぎ、溜まっているコメントをすべて回収する"""
    try:
        # 接続設定
        sock = socket.socket()
        sock.settimeout(2.5) # 応答を待つ時間
        sock.connect(("irc.chat.twitch.tv", 6667))
        
        token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
        sock.send(f"PASS {token}\r\n".encode("utf-8"))
        sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
        sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
        
        # ログインから現在までのメッセージが届くのを少し待つ
        time.sleep(1.0)
        data = sock.recv(16384).decode("utf-8")
        sock.close()
        
        st.session_state.conn_status = "🟢 正常に巡回中"
        
        messages = []
        for line in data.split("\r\n"):
            if "PRIVMSG" in line:
                user = line.split("!")[0][1:]
                msg = line.split(f"#{TW_CHANNEL} :", 1)[1].strip()
                messages.append(f"{user}: {msg}")
        
        return messages if messages else None
    except Exception as e:
        st.session_state.conn_status = f"🔴 接続エラー: {str(e)[:20]}"
        return None

# --- 3. AI思考エンジン ---
def generate_ai_thought(comments):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
    
    if comments:
        comment_str = " | ".join(comments[-5:]) # 直近5件を材料にする
        prompt = f"毒舌AI配信者として、視聴者のコメント「{comment_str}」にまず皮肉を言い、そこから自分の「今ムカついている話題」へ繋げて150文字程度で喋って。「」内のセリフのみ。"
    else:
        prompt = "チャットが静かなので、毒舌AI配信者として視聴者のやる気のなさを煽りつつ、最近の『くだらない流行り』について150文字程度で毒を吐いて。「」内のセリフのみ。"

    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "（思考回路がオーバーヒートしたわ。あなたのせいじゃない？）"

# --- 4. メイン UI ---
st.title("🤖 リアルタイムAI配信者（安定版）")

# ステータス表示
st.metric("Twitch サーバー状況", st.session_state.conn_status)

# 自動更新 JS（primary属性のボタンをクリックさせる）
st.components.v1.html(f"""
    <script>
    setTimeout(function(){{
        window.parent.document.querySelector('button[kind="primary"]').click();
    }}, {refresh_rate * 1000});
    </script>
""", height=0)

if st.button("🎙 手動/自動トーク実行", type="primary"):
    with st.spinner("チャットを読み込み中..."):
        # 1. チャットをさらってくる
        current_comments = get_twitch_messages_stable()
        
        # 2. AIが考える
        thought = generate_ai_thought(current_comments)
        
        if thought:
            st.session_state.chat_log.append(thought)
            # 3. 音声再生
            clean_text = thought.replace("「","").replace("」","")
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{clean_text}");
                msg.lang = "ja-JP";
                msg.pitch = 0.8;
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)

# 履歴表示
st.divider()
for m in reversed(st.session_state.chat_log):
    st.chat_message("assistant", avatar="🤖").write(m)

if not (ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN):
    st.warning("サイドバーの設定をすべて埋めてください。")
