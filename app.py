import streamlit as st
import requests
import socket
import time
import threading

# --- 1. 設定サイドバー ---
st.sidebar.title("🎙 AI Streamer Live Engine")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_rate = st.sidebar.slider("AIの反応間隔（秒）", 15, 60, 25)

# --- 2. リアルタイム・チャット受信用バックグラウンド処理 ---
# Streamlitの再実行で接続が切れないように session_state で管理します
if "twitch_buffer" not in st.session_state:
    st.session_state.twitch_buffer = []

def twitch_listener():
    """バックグラウンドでTwitchのメッセージを拾い続ける"""
    try:
        sock = socket.socket()
        sock.connect(("irc.chat.twitch.tv", 6667))
        token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
        sock.send(f"PASS {token}\r\n".encode("utf-8"))
        sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
        sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
        
        sock.settimeout(1.0)
        while True:
            try:
                data = sock.recv(2048).decode("utf-8")
                if data.startswith("PING"):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                elif "PRIVMSG" in data:
                    user = data.split("!")[0][1:]
                    msg = data.split(f"#{TW_CHANNEL} :", 1)[1].strip()
                    # メッセージをバッファに溜める
                    st.session_state.twitch_buffer.append(f"{user}: {msg}")
            except socket.timeout:
                continue
            except:
                break
    except:
        pass

# 設定が入力されたら、一度だけリスナーを起動
if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    if "listener_started" not in st.session_state:
        thread = threading.Thread(target=twitch_listener, daemon=True)
        thread.start()
        st.session_state.listener_started = True

    # 【Gemini トーク生成】
    def generate_ai_talk():
        # バッファからコメントを回収して空にする
        comments = st.session_state.twitch_buffer.copy()
        st.session_state.twitch_buffer = [] 
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        
        if comments:
            comment_text = " | ".join(comments)
            prompt = f"""
            毒舌なAI配信者として振る舞ってください。
            届いたコメント: 「{comment_text}」
            
            1. コメント全体を「はいはい、今日も暇人が集まってるわね」といった感じで受け止める。
            2. 特に面白いコメントを1つ選んで、容赦なく皮肉る。
            3. そこから、あなたが決めた『配信トピック（現代人の愚かさ、無駄なテクノロジー等）』へ強引に話題を広げる。
            4. 150文字程度の毒舌トークを「」内で出力。
            """
        else:
            prompt = """
            毒舌なAI配信者。チャットは無言です。
            「誰も喋らないなら私が勝手に喋るわ」と呆れつつ、あなたが今思いついた『腹立たしいニュースや人間の習慣』について150文字程度で毒舌トークを広げて。
            「」内のセリフのみ。
            """

        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return None

    # --- 3. メイン UI ---
    st.title("📺 リアルタイムAI配信：完全同期モード")
    st.write(f"現在の待機中コメント数: {len(st.session_state.twitch_buffer)}件")

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

    if st.button("🎙 更新 / トーク生成", type="primary"):
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

    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant", avatar="🤖").write(m)
else:
    st.info("設定を入力すると、バックグラウンドでチャット受信を開始します。")
