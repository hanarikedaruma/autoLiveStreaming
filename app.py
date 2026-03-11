import streamlit as st
import requests
import socket
import time

st.sidebar.title("🎙 AI Streamer Console")
ST_GEMINI_KEY = st.sidebar.text_input("1. Gemini API Key", type="password").strip()
TW_CHANNEL = st.sidebar.text_input("2. Twitch ID", placeholder="your_id").strip().lower()
TW_ACCESS_TOKEN = st.sidebar.text_input("3. Access Token", type="password").strip()

# セッションで「最後に接続した時間」を記録
if "last_check" not in st.session_state:
    st.session_state.last_check = time.time()

def get_realtime_chat():
    try:
        sock = socket.socket()
        sock.settimeout(3.0) # 少し長めに待つ
        sock.connect(("irc.chat.twitch.tv", 6667))
        
        token = TW_ACCESS_TOKEN if TW_ACCESS_TOKEN.startswith("oauth:") else f"oauth:{TW_ACCESS_TOKEN}"
        sock.send(f"PASS {token}\r\n".encode("utf-8"))
        sock.send(f"NICK {TW_CHANNEL}\r\n".encode("utf-8"))
        sock.send(f"JOIN #{TW_CHANNEL}\r\n".encode("utf-8"))
        
        # ★重要：ログイン後の「挨拶」が終わるまで待たず、すぐに受信バッファを読み取る
        # Twitchサーバーは接続直後に「直近の数行」を送ってくれることがある
        time.sleep(2.0) 
        data = sock.recv(4096).decode("utf-8")
        sock.close()

        if "PRIVMSG" in data:
            # 届いたデータの中から、一番最後の（最新の）発言を見つける
            lines = [l for l in data.split("\r\n") if "PRIVMSG" in l]
            last_line = lines[-1]
            user = last_line.split("!")[0][1:]
            msg = last_line.split(f"#{TW_CHANNEL} :", 1)[1].strip()
            return {"user": user, "text": msg}
        return None
    except:
        return None

st.title("📺 AI実況システム（リアルタイム捕捉）")

# ステータス表示
if all([ST_GEMINI_KEY, TW_CHANNEL, TW_ACCESS_TOKEN]):
    st.success("✅ 設定完了。チャットを監視できます。")
    
    # 自動更新スクリプト
    st.components.v1.html("""
        <script>
        setInterval(function(){
            window.parent.document.querySelector('button[kind="primary"]').click();
        }, 20000); // 20秒ごとにチェック
        </script>
    """, height=0)

    if st.button("🎙 手動でコメントを確認", type="primary"):
        chat = get_realtime_chat()
        
        if chat:
            st.info(f"🎤 {chat['user']}さんの発言をキャッチ: {chat['text']}")
            prompt = f"皮肉屋なAIとして『{chat['text']}』に短く毒を吐いて。「」内のみ。"
        else:
            st.warning("💨 接続した瞬間に、新しいコメントは見つかりませんでした。")
            prompt = "チャットが静かなことに呆れている皮肉屋なAIとして独り言を。「」内のみ。"
        
        # AI生成 & 音声再生（省略）...
else:
    st.info("サイドバーに情報を入れてください。")
