import streamlit as st
import socket
import threading
import time
import requests
from queue import Queue

# --- 1. 基本設定（サイドバー） ---
st.set_page_config(page_title="AI Streamer Pro", page_icon="🎙")
st.sidebar.title("🎙 AI Streamer Live Engine")

ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password", help="oauth:xxxの形式").strip()
refresh_rate = st.sidebar.slider("AIが喋る間隔（秒）", 15, 120, 30)

# セッション管理（再起動対策）
if "chat_queue" not in st.session_state:
    st.session_state.chat_queue = Queue()
if "conn_status" not in st.session_state:
    st.session_state.conn_status = "🔴 未接続"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 2. バックグラウンド：Twitch常時監視スレッド ---
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
            sock.send("CAP REQ :twitch.tv/tags twitch.tv/commands\r\n".encode("utf-8"))
            
            st.session_state.conn_status = "🟢 常時同期中"
            
            while True:
                data = sock.recv(2048).decode("utf-8")
                if not data: break
                if data.startswith("PING"):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                elif "PRIVMSG" in data:
                    user = data.split("!")[0][1:]
                    msg = data.split(f"#{channel} :", 1)[1].strip()
                    queue.put({"user": user, "text": msg})
        except:
            st.session_state.conn_status = "🔴 再接続中..."
            time.sleep(5)

# スレッド起動（一度だけ実行）
if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    if "thread_started" not in st.session_state:
        t = threading.Thread(
            target=twitch_listener, 
            args=(TW_CHANNEL, TW_ACCESS_TOKEN, st.session_state.chat_queue), 
            daemon=True
        )
        t.start()
        st.session_state.thread_started = True

# --- 3. AI思考エンジン：Gemini API (安全フィルター緩和版) ---
def generate_ai_talk():
    # キューから全てのコメントを回収
    collected = []
    while not st.session_state.chat_queue.empty():
        collected.append(st.session_state.chat_queue.get())
    
    # プロンプト作成
    if collected:
        summary = "\n".join([f"- {m['user']}: {m['text']}" for m in collected])
        prompt = f"""
        あなたは知性的で皮肉屋なAI配信者です。
        視聴者から以下のコメントが届きました：
        {summary}

        【指示】
        1. まず「{collected[0]['user']}たちが何か言ってるわね」とコメントを拾って皮肉を言う。
        2. コメントから共通のテーマを見つけ、そこから「人間社会の滑稽さ」に繋げる。
        3. 150文字程度の毒舌フリートークを「」内で出力してください。
        """
    else:
        prompt = "チャットが静かです。皮肉屋なAI配信者として、視聴者の無関心を煽りつつ、自発的に最近の不快な話題で150文字程度喋って。「」内のみ。"

    # API呼び出し設定
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }

    try:
        res = requests.post(url, json=payload, timeout=15)
        res_json = res.json()
        
        if 'candidates' in res_json and res_json['candidates'][0].get('content'):
            return res_json['candidates'][0]['content']['parts'][0]['text']
        elif 'error' in res_json:
            return f"（APIエラー: {res_json['error']['message']}）"
        else:
            return "（AIが沈黙したわ。内容が過激すぎたかしら？）"
    except Exception as e:
        return f"（通信エラー: {str(e)}）"

# --- 4. メイン UI 表示 ---
st.title("🤖 AI Streamer Pro：ライブ稼働中")

col1, col2 = st.columns(2)
col1.metric("Twitch接続", st.session_state.conn_status)
col2.metric("待機中コメント", st.session_state.chat_queue.qsize())

# 自動リフレッシュ用 JavaScript
st.components.v1.html(f"""
    <script>
    setTimeout(function(){{
        window.parent.document.querySelector('button[kind="primary"]').click();
    }}, {refresh_rate * 1000});
    </script>
""", height=0)

if st.button("🎙 次のトークを生成（手動/自動）", type="primary"):
    with st.spinner("AIが思考中..."):
        talk = generate_ai_talk()
        if talk:
            st.session_state.chat_history.append(talk)
            # 音声再生
            clean_text = talk.replace("「", "").replace("」", "").replace("\n", " ")
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{clean_text}");
                msg.lang = "ja-JP";
                msg.pitch = 0.8;
                msg.rate = 1.0;
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)

# 履歴の表示
st.divider()
for m in reversed(st.session_state.chat_history):
    st.chat_message("assistant", avatar="🤖").write(m)

if not (ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN):
    st.info("サイドバーにAPIキー等を入力して、配信をスタートしてください。")
