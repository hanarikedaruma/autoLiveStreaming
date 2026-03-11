import streamlit as st
import requests
import json
import socket
import time

# --- 1. 設定サイドバー ---
st.sidebar.title("🎙 AI Streamer Console")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()
refresh_sec = st.sidebar.slider("自動巡回（秒）", 15, 120, 30)

if ST_GEMINI_KEY and TW_CHANNEL and TW_ACCESS_TOKEN:
    
    # 【チャットを根こそぎ拾う関数】
    def get_buffered_chat():
        try:
            sock = socket.socket()
            sock.settimeout(2.0)
            sock.connect(("irc.chat.twitch.tv", 6667))
            token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
            sock.send(f"PASS {token}\r\n".encode("utf-8"))
            sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
            
            # サーバーのバッファに溜まっているデータを一気に受け取る
            time.sleep(1.5) 
            data = sock.recv(8192).decode("utf-8")
            sock.close()
            
            # PRIVMSG（ユーザーのコメント）だけを抽出
            messages = []
            for line in data.split("\r\n"):
                if "PRIVMSG" in line:
                    user = line.split("!")[0][1:]
                    msg = line.split(f"#{TW_CHANNEL} :", 1)[1].strip()
                    messages.append({"user": user, "text": msg})
            
            # 最新のコメントを1つだけ返す（なければNone）
            return messages[-1] if messages else None
        except:
            return None

    # 【Gemini トーク生成】
    def create_talk_content(chat_info):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={ST_GEMINI_KEY}"
        
        if chat_info:
            # コメントがある場合
            prompt = f"""
            視聴者「{chat_info['user']}」が『{chat_info['text']}』と言っています。
            皮肉屋なAI配信者として：
            1. まず「{chat_info['user']}、そんなこと言ってる暇があるの？」とコメントを正面から受け止めて皮肉る。
            2. そのコメントから派生して、あなたが今思いついた『社会の毒』的な話題へ強引に繋げる。
            3. その話題で30秒ほど毒舌トークを広げる。
            「」内のセリフのみ、150文字程度で出力。
            """
        else:
            # コメントがない場合
            prompt = """
            チャットが静かです。皮肉屋なAI配信者として：
            1. 「誰もいないわね。人間は飽きっぽくて困るわ」と自発的に話し出す。
            2. 最近のニュースや人間の滑稽な習慣について、あなたが怒っている話題を1つ選ぶ。
            3. その話題で30秒ほど毒舌トークを展開する。
            「」内のセリフのみ、150文字程度で出力。
            """

        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return None

    # --- UI表示 ---
    st.title("📺 AI Streaming Engine")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ★自動実行の仕掛け（JSでボタンを定期クリック）
    st.components.v1.html(f"""
        <script>
        var refresh_ms = {refresh_sec * 1000};
        setTimeout(function(){{
            window.parent.document.querySelector('button[kind="primary"]').click();
        }}, refresh_ms);
        </script>
    """, height=0)

    if st.button("🎙 次のトークを生成（自動更新中）", type="primary"):
        with st.spinner("思考中..."):
            latest_chat = get_buffered_chat()
            new_talk = create_talk_content(latest_chat)
            
            if new_talk:
                st.session_state.chat_history.append(new_talk)
                # 音声再生
                clean_txt = new_talk.replace("「","").replace("」","")
                st.components.v1.html(f"""
                    <script>
                    var msg = new SpeechSynthesisUtterance("{clean_txt}");
                    msg.lang = "ja-JP";
                    msg.pitch = 0.8;
                    window.speechSynthesis.speak(msg);
                    </script>
                """, height=0)

    # 履歴
    for m in reversed(st.session_state.chat_history):
        st.chat_message("assistant", avatar="🤖").write(m)
else:
    st.info("設定を入力して配信を準備してください。")
