import streamlit as st
import requests
import json
import socket
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🎙 AI Streamer Live")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
# 配信のテンポ（更新間隔）を調整
refresh_rate = st.sidebar.slider("更新間隔（秒）", 15, 60, 25)

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    
    # 【チャットバッファ全取得関数】
    # 前回のリフレッシュから今回までに届いたメッセージをすべて吸い出します
    def get_all_new_messages():
        try:
            sock = socket.socket()
            sock.settimeout(2.0)
            sock.connect(("irc.chat.twitch.tv", 6667))
            token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
            sock.send(f"PASS {token}\r\n".encode("utf-8"))
            sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
            
            # サーバーから流れてくるデータを一気に読み取る
            time.sleep(1.5) 
            data = sock.recv(16384).decode("utf-8") # バッファサイズを大きく
            sock.close()
            
            comments = []
            for line in data.split("\r\n"):
                if "PRIVMSG" in line:
                    user = line.split("!")[0][1:]
                    msg = line.split(f"#{TW_CHANNEL} :", 1)[1].strip()
                    comments.append(f"{user}: {msg}")
            
            return comments if comments else None
        except:
            return None

    # 【AIトーク生成ロジック】
    def generate_live_talk(comments):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        
        if comments:
            comment_summary = " | ".join(comments)
            prompt = f"""
            あなたは毒舌なAI配信者です。
            今、チャットに以下のコメントが届きました: 「{comment_summary}」

            【指示】
            1. まず、届いたコメント全体を「ふん、みんな勝手なこと言ってるわね」と受け止める。
            2. 特に気になったコメントに1つ触れて、鋭く皮肉を言う。
            3. そこから強引に、あなたが今決めた「配信の話題（テクノロジー、社会、人間の愚かさなど）」に繋げる。
            4. 最後に「で、あなたたちはどう思うわけ？」と視聴者に投げかけて締める。
            
            「」内のセリフのみ、200文字程度で出力してください。
            """
        else:
            prompt = """
            あなたは皮肉屋なAI配信者。チャットは静かです。
            
            【指示】
            1. 「誰も喋らないなら私が適当に話題を振ってあげるわ」と前置きする。
            2. あなたが今腹を立てている「世の中の矛盾」について1つ話題を出し、30秒ほど毒舌トークを広げる。
            
            「」内のセリフのみ、200文字程度で出力してください。
            """

        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return None

    # --- UI 構築 ---
    st.title("📺 AIライブ実況：リアルタイム捕捉")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ★自動更新 JavaScript
    # 一定時間ごとに「更新ボタン」を自動クリックしてトークを回す
    st.components.v1.html(f"""
        <script>
        var timer = {refresh_rate * 1000};
        setTimeout(function(){{
            window.parent.document.querySelector('button[kind="primary"]').click();
        }}, timer);
        </script>
    """, height=0)

    if st.button("🎙 次のトークを生成（自動更新）", type="primary"):
        with st.spinner("視聴者の声を収集して、思考を整理中..."):
            new_comments = get_all_new_messages()
            talk = generate_live_talk(new_comments)
            
            if talk:
                st.session_state.chat_history.append(talk)
                # 音声合成（ブラウザのSpeechSynthesisを使用）
                clean_talk = talk.replace("「","").replace("」","")
                st.components.v1.html(f"""
                    <script>
                    var msg = new SpeechSynthesisUtterance("{clean_talk}");
                    msg.lang = "ja-JP";
                    msg.pitch = 0.8;
                    msg.rate = 1.05;
                    window.speechSynthesis.speak(msg);
                    </script>
                """, height=0)

    # 履歴を新しい順に表示
    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant", avatar="🤖").write(m)

else:
    st.info("サイドバーにキーを入力してください。接続を開始します。")
