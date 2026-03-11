import streamlit as st
import socket
import threading
import time
import requests
from queue import Queue

# --- 1. 基本設定 ---
st.set_page_config(page_title="AI Streamer 2.7 Pro", page_icon="🎙", layout="wide")

# 視認性重視のCSS
st.markdown("""
    <style>
    [data-testid="stChatMessage"] { background-color: #262730 !important; border: 1px solid #464b5d; color: white !important; }
    [data-testid="stChatMessage"] p { color: #ffffff !important; font-size: 1.1rem; }
    .buffer-box { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.sidebar.title("🎙 AI Streamer Setting")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("AIが思考する間隔（秒）", 10, 60, 30)

# セッション管理
if "chat_queue" not in st.session_state: st.session_state.chat_queue = Queue()
if "accumulated_msgs" not in st.session_state: st.session_state.accumulated_msgs = [] # 蓄積用バッファ
if "conn_status" not in st.session_state: st.session_state.conn_status = "🔴 未接続"
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- 2. Twitch常時監視（コメントを取得して即バッファへ） ---
def twitch_listener(channel, token, queue):
    while True:
        try:
            sock = socket.socket()
            sock.settimeout(10.0)
            sock.connect(("irc.chat.twitch.tv", 6667))
            auth_token = token if token.startswith("oauth:") else f"oauth:{token}"
            sock.send(f"PASS {auth_token}\r\n".encode("utf-8"))
            sock.send(f"NICK {channel}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{channel}\r\n".encode("utf-8"))
            st.session_state.conn_status = "🟢 同期中"
            while True:
                data = sock.recv(2048).decode("utf-8")
                if not data: break
                if data.startswith("PING"):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                elif "PRIVMSG" in data:
                    user = data.split("!")[0][1:]
                    msg = data.split(f"#{channel} :", 1)[1].strip()
                    # ここで即座にキューへ入れる
                    queue.put({"user": user, "text": msg})
        except:
            st.session_state.conn_status = "🔴 再接続中"
            time.sleep(5)

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN and "thread_started" not in st.session_state:
    t = threading.Thread(target=twitch_listener, args=(TW_CHANNEL, TW_ACCESS_TOKEN, st.session_state.chat_queue), daemon=True)
    t.start()
    st.session_state.thread_started = True

# --- 3. コメント蓄積処理（UI更新のたびに実行） ---
# キューに入っている未処理コメントを accumulated_msgs に移す
while not st.session_state.chat_queue.empty():
    st.session_state.accumulated_msgs.append(st.session_state.chat_queue.get())

# --- 4. AI思考エンジン（蓄積されたコメントをまとめて処理） ---
def generate_ai_talk():
    # 蓄積されたコメントを確認
    msgs = st.session_state.accumulated_msgs
    
    if msgs:
        # 蓄積コメントをプロンプト化
        summary = "\n".join([f"- {m['user']}: {m['text']}" for m in msgs])
        # 使用したバッファをクリア
        st.session_state.accumulated_msgs = []
        
        prompt = f"""知性的で皮肉屋なAI配信者として振る舞って。
        【蓄積された視聴者コメント】
        {summary}
        
        指示：
        1. 複数のコメントの流れを汲み取り、「みんな勝手なこと言ってるわね」と総括して。
        2. 特に印象的な意見を一つ選び、その矛盾や浅はかさを毒舌で論理的に指摘して。
        3. 最後は不条理な社会問題に強引に繋げて、150文字程度で喋って。
        4. セリフは「」内のみ。"""
    else:
        prompt = "チャットが静かです。皮肉屋AIとして、視聴者の怠慢を煽りつつ、最近の不条理なニュースについて150文字程度で独り言を言って。「」内のみ。"

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={ST_GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in [
            "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_DANGEROUS_CONTENT"
        ]]
    }
    try:
        res = requests.post(url, json=payload, timeout=15)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return None

def run_ai_cycle():
    with st.spinner("蓄積されたコメントを分析中..."):
        talk = generate_ai_talk()
        if talk:
            st.session_state.chat_history.append(talk)
            st.session_state.last_talk = talk.replace("「", "").replace("」", "").replace("\n", " ")

# --- 5. メイン画面表示 ---
st.title("🤖 AI Streamer Pro v2.7")

c1, c2, c3 = st.columns(3)
c1.metric("Twitch同期", st.session_state.conn_status)
c2.metric("蓄積済みコメント数", len(st.session_state.accumulated_msgs))
c3.metric("次回のAI思考まで", f"{refresh_rate}秒間隔")

# 【新規】現在蓄積されているコメントを表示するエリア
if st.session_state.accumulated_msgs:
    with st.expander("📥 現在蓄積中のコメント（次のトークで処理されます）", expanded=True):
        for m in st.session_state.accumulated_msgs[-5:]: # 直近5件を表示
            st.write(f"**{m['user']}**: {m['text']}")

st.divider()

# トーク履歴
for m in reversed(st.session_state.chat_history[-10:]):
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(m)

# 操作系
if st.button("🎙 話題を更新（自動巡回）", type="primary", on_click=run_ai_cycle):
    pass

# --- 6. JS (音声・更新) ---
if "last_talk" in st.session_state and st.session_state.last_talk:
    st.components.v1.html(f"""
        <script>
        var msg = new SpeechSynthesisUtterance("{st.session_state.last_talk}");
        msg.lang = "ja-JP"; msg.pitch = 0.8; msg.rate = 1.1;
        window.speechSynthesis.speak(msg);
        </script>
    """, height=0)
    st.session_state.last_talk = None

st.components.v1.html(f"""
    <script>
    setTimeout(function(){{ window.parent.document.querySelector('button[kind="primary"]').click(); }}, {refresh_rate * 1000});
    </script>
""", height=0)
