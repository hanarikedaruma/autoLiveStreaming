import streamlit as st
import socket
import threading
import time
import requests
from queue import Queue

# --- 1. 基本設定 ---
st.sidebar.title("🎙 AI Streamer Engine")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("AIが喋る間隔（秒）", 15, 60, 30)

# セッション管理（リロードしても消さない）
if "chat_queue" not in st.session_state:
    st.session_state.chat_queue = Queue()
if "conn_status" not in st.session_state:
    st.session_state.conn_status = "🔴 未接続"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 2. 常時同期スレッド（修正版） ---
def twitch_listener(channel, token, queue):
    while True:
        try:
            sock = socket.socket()
            sock.settimeout(5.0)
            sock.connect(("irc.chat.twitch.tv", 6667))
            auth_token = token if token.startswith("oauth:") else f"oauth:{token}"
            sock.send(f"PASS {auth_token}\r\n".encode("utf-8"))
            sock.send(f"NICK {channel}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{channel}\r\n".encode("utf-8"))
            
            st.session_state.conn_status = "🟢 常時同期中"
            
            while True:
                data = sock.recv(2048).decode("utf-8")
                if not data: break
                if data.startswith("PING"):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                elif "PRIVMSG" in data:
                    user = data.split("!")[0][1:]
                    msg = data.split(f"#{channel} :", 1)[1].strip()
                    # 確実にQueueに入れる
                    queue.put({"user": user, "text": msg})
        except:
            st.session_state.conn_status = "🔴 再接続中..."
            time.sleep(5)

# スレッド起動
if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    if "thread_started" not in st.session_state:
        t = threading.Thread(target=twitch_listener, args=(TW_CHANNEL, TW_ACCESS_TOKEN, st.session_state.chat_queue), daemon=True)
        t.start()
        st.session_state.thread_started = True

# --- 3. トーク生成コア（ここを強化） ---
def process_and_generate_talk():
    # 貯金箱（Queue）から全コメントを回収
    collected_messages = []
    while not st.session_state.chat_queue.empty():
        collected_messages.append(st.session_state.chat_queue.get())
    
    # AIへの指示（プロンプト）をより厳格に
    if collected_messages:
        # 視聴者ごとの発言をリスト化
        summary = "\n".join([f"- {m['user']}: {m['text']}" for m in collected_messages])
        prompt = f"""
        あなたは毒舌で知性的なAI配信者です。
        現在、以下のコメントが届いています：
        {summary}

        【ミッション】
        1. 届いたコメントの内容を「はいはい、{collected_messages[0]['user']}たちが何か言ってるわね」と受け止める。
        2. それらのコメントから共通するテーマ、あるいは特にツッコミ甲斐のある内容を1つ選ぶ。
        3. その話題を皮切りに、あなたが今思いついた「人間社会の滑稽さ」についての毒舌フリートークを150文字程度で展開して。
        4. セリフは「」で囲んで出力してください。
        """
    else:
        prompt = "チャットが静かです。皮肉屋なAI配信者として、視聴者の無関心を煽りつつ、自発的に今ムカついている話題を1つ選んで150文字程度で喋って。「」内のみ。"

    # Gemini API 呼び出し
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        talk = res.json()['candidates'][0]['content']['parts'][0]['text']
        return talk
    except Exception as e:
        return f"（エラーが発生したわ。{e}）"

# --- 4. メイン UI ---
st.title("🎙 実況中：AIトークエンジン")

col1, col2 = st.columns(2)
col1.metric("接続状態", st.session_state.conn_status)
col2.metric("待機中コメント", st.session_state.chat_queue.qsize())

# 自動リフレッシュ
st.components.v1.html(f"""
    <script>
    setTimeout(function(){{
        window.parent.document.querySelector('button[kind="primary"]').click();
    }}, {refresh_rate * 1000});
    </script>
""", height=0)

if st.button("🎙 思考 & トーク実行", type="primary"):
    with st.spinner("コメントを料理中..."):
        new_talk = process_and_generate_talk()
        if new_talk:
            st.session_state.chat_history.append(new_talk)
            # 音声再生
            clean_talk = new_talk.replace("「","").replace("」","")
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{clean_talk}");
                msg.lang = "ja-JP";
                msg.pitch = 0.8;
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)

# 履歴表示
for m in reversed(st.session_state.chat_history):
    st.chat_message("assistant", avatar="🤖").write(m)
