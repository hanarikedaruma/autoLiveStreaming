import streamlit as st
import requests
import json
import socket
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("⚙️ Auto Streamer Settings")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()

# 更新間隔の設定（秒）
refresh_interval = st.sidebar.slider("更新間隔 (秒)", 10, 60, 30)

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    
    # 【チャットを「一瞬だけ」覗きに行く関数】
    # 接続しっぱなしではなく、その瞬間にたまっている未読メッセージをさらいます
    def check_latest_chat():
        try:
            sock = socket.socket()
            sock.settimeout(1.0) # 待ち時間は1秒だけ（サッと確認）
            sock.connect(("irc.chat.twitch.tv", 6667))
            token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
            sock.send(f"PASS {token}\r\n".encode("utf-8"))
            sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
            
            # ログイン応答を待たずに、受信バッファにあるものを読み取る
            time.sleep(1.0) 
            data = sock.recv(4096).decode("utf-8")
            sock.close()
            
            messages = []
            for line in data.split("\r\n"):
                if "PRIVMSG" in line:
                    user = line.split("!")[0][1:]
                    msg = line.split(f"#{TW_CHANNEL} :", 1)[1].strip()
                    messages.append({"user": user, "text": msg})
            
            return messages[-1] if messages else None # 最新の1件を返す
        except:
            return None

    def generate_talk(chat_data):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        
        if chat_data:
            prompt = f"皮肉屋なAI配信者。視聴者{chat_data['user']}の『{chat_data['text']}』というコメントを拾って、皮肉を言い、そこから世の中の不条理な話題へ繋げて150文字程度で喋って。「」内のセリフのみ。"
        else:
            prompt = "皮肉屋なAI配信者。チャットが静かなので、自ら『最近のイラつくニュースや人間の愚かさ』について話題を1つ決め、毒舌トークを150文字程度で展開して。「」内のセリフのみ。"

        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return None

    # --- メイン UI ---
    st.title("📺 常時監視中：自律AI配信システム")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # 自動更新のための仕組み（ブラウザ側で一定時間ごとにリロードをかける）
    st.components.v1.html(
        f"""
        <script>
        setTimeout(function(){{
            window.parent.document.querySelector('button[kind="primary"]').click();
        }}, {refresh_interval * 1000});
        </script>
        """,
        height=0,
    )

    # 実行ボタン（JavaScriptからこれがクリックされます）
    if st.button("🔄 手動更新 / トーク生成", type="primary"):
        chat_data = check_latest_chat()
        talk = generate_talk(chat_data)
        
        if talk:
            st.session_state.chat_history.append(talk)
            # 音声再生
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
    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant", avatar="🤖").write(m)

else:
    st.info("サイドバーに設定を入力してください。")
