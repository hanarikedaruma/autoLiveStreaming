import streamlit as st
import socket
import threading
import time
import requests
from queue import Queue

# --- 1. 基本設定 ---
st.set_page_config(page_title="AI Streamer 2.8 Strategy", page_icon="🎙", layout="wide")

# 視認性重視のCSS（黒背景に白文字を徹底）
st.markdown("""
    <style>
    [data-testid="stChatMessage"] { background-color: #262730 !important; border: 1px solid #464b5d; }
    [data-testid="stChatMessage"] p { color: #ffffff !important; font-size: 1.1rem; }
    .stMetric { background-color: #0e1117; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    </style>
""", unsafe_allow_html=True)

st.sidebar.title("🎙 Streaming Strategy")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("AIの思考スパン（秒）", 10, 60, 25)

if "chat_queue" not in st.session_state: st.session_state.chat_queue = Queue()
if "accumulated_msgs" not in st.session_state: st.session_state.accumulated_msgs = []
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "current_topic" not in st.session_state: st.session_state.current_topic = "フリートーク"

# --- 2. Twitch常時監視（コメント蓄積） ---
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
            st.session_state.conn_status = "🟢 接続中"
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
            st.session_state.conn_status = "🔴 再接続"
            time.sleep(5)

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN and "thread_started" not in st.session_state:
    t = threading.Thread(target=twitch_listener, args=(TW_CHANNEL, TW_ACCESS_TOKEN, st.session_state.chat_queue), daemon=True)
    t.start()
    st.session_state.thread_started = True

# 未処理コメントの回収
while not st.session_state.chat_queue.empty():
    st.session_state.accumulated_msgs.append(st.session_state.chat_queue.get())

# --- 3. AI思考エンジン（種まき＆深掘りロジック） ---
def generate_ai_talk():
    msgs = st.session_state.accumulated_msgs
    engagement = len(msgs)
    
    if engagement >= 3:
        # 【深掘りモード】反応が良いので、今の話題をさらに広げる
        st.session_state.accumulated_msgs = [] # 消化
        summary = "\n".join([f"- {m['user']}: {m['text']}" for m in msgs])
        prompt = f"""
        【状況】チャットが盛り上がっています！
        【現在の話題】{st.session_state.current_topic}
        【リスナーの反応】
        {summary}
        
        【指示】
        今の話題に対してリスナーが良い食いつきを見せています。
        1. 彼らのコメントを肯定的に、あるいはさらに刺激するように拾って。
        2. 今の話題からさらに一歩踏み込んだ「衝撃の事実」や「過激な自説」を語って。
        150文字程度で、熱量を上げて喋って。「」内のみ。
        """
    else:
        # 【種まきモード】反応が薄い、あるいは静かなので、新しいエピソードを投下
        prompt = f"""
        【状況】チャットが落ち着いています。
        【前回の話題】{st.session_state.current_topic}
        
        【指示】
        リスナーの関心を引くために、全く新しい「エピソードの種」をまいてください。
        1. 「そういえば、こんなことあったんだけど…」と切り出して。
        2. ネットで見つけた奇妙な事件、技術の不条理、あるいはAIとしての奇妙な体験談を一つ話して。
        3. 最後に「あなたたちならどう思う？」と、リスナーが答えやすい問いかけをして。
        150文字程度で、好奇心をそそるように。「」内のみ。
        """

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={ST_GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, json=payload, timeout=15)
        text = res.json()['candidates'][0]['content']['parts'][0]['text']
        # 新しい話題をセッションに保存
        st.session_state.current_topic = text[:30]
        return text
    except:
        return None

def run_ai_cycle():
    talk = generate_ai_talk()
    if talk:
        st.session_state.chat_history.append(talk)
        st.session_state.last_talk = talk.replace("「", "").replace("」", "").replace("\n", " ")

# --- 4. メイン UI ---
st.title("🎙 AI Streamer Strategy Pro")

c1, c2, c3 = st.columns(3)
c1.metric("話題の熱量", "🔥 深掘り中" if len(st.session_state.accumulated_msgs) >= 3 else "🌱 種まき中")
c2.metric("待機中の声", len(st.session_state.accumulated_msgs))
c3.metric("現在のトピック", st.session_state.current_topic[:15] + "...")

st.divider()

# 履歴
for m in reversed(st.session_state.chat_history[-10:]):
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(m)

if st.button("🎙 トーク更新（自動）", type="primary", on_click=run_ai_cycle):
    pass

# --- 5. JS (音声・更新) ---
if "last_talk" in st.session_state and st.session_state.last_talk:
    st.components.v1.html(f"""
        <script>
        var msg = new SpeechSynthesisUtterance("{st.session_state.last_talk}");
        msg.lang = "ja-JP"; msg.pitch = 0.9; msg.rate = 1.1;
        window.speechSynthesis.speak(msg);
        </script>
    """, height=0)
    st.session_state.last_talk = None

st.components.v1.html(f"""
    <script>
    setTimeout(function(){{ window.parent.document.querySelector('button[kind="primary"]').click(); }}, {refresh_rate * 1000});
    </script>
""", height=0)
