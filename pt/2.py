import os
import re
import requests
import time
import random

# 环境变量
ROUSI_COOKIE    = os.environ.get('ROUSI', '').strip()
TELEGRAM_CHAT_ID = os.environ.get('TG_USER_ID', '').strip()
WORKER_DOMAIN    = os.environ.get('DOMAIN', '').strip()
WORKER_KEY       = os.environ.get('WORKER_KEY', '').strip()

# 请求头：注入 Cookie
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.6778.205 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate",       # requests 默认支持 gzip/deflate
    "Connection": "keep-alive",
    "Referer": "https://rousi.zip/index.php",  # 来源页面
    "Cookie": ROUSI_COOKIE                    # 注入登录态
}

final_messages = []

def add_message(msg: str):
    print(msg)
    final_messages.append(msg)

def signin_rousi():
    """在 rousi.zip 上执行签到"""
    if not ROUSI_COOKIE:
        add_message("❌ 未检测到 ROUSI 环境变量（Cookie），请检查。")
        return

    # 1) 随机延迟，模拟真实“先想一想再点”的人类行为
    delay1 = random.uniform(5, 60)   # 5～60 秒之间随机
    time.sleep(delay1)
    
    # 2) 先 GET 首页，执行一次页面加载
    try:
        resp_index = requests.get("https://rousi.zip/index.php", headers=HEADERS, timeout=10)
        if resp_index.status_code != 200:
            add_message(f"⚠️ 首页请求异常，状态码：{resp_index.status_code}")
            # 虽然首页异常也可以选择中断，但这里我们继续尝试签到
    except Exception as e:
        add_message(f"⚠️ 首页请求出错：{e}")

    # 3) 再随机短暂停顿，模拟点击前的停留
    time.sleep(random.uniform(1, 5))

    # 4) 签到
    url = "https://rousi.zip/attendance.php"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            # 根据页面实际提示调整正则
            m = re.search(r'<div[^>]*class=["\']text-success[^>]*>(.*?)</div>', resp.text, re.S)
            if m:
                add_message(f"✅ 签到成功：{m.group(1).strip()}")
            else:
                add_message("✅ 签到完成，未匹配到页面提示。")
        else:
            add_message(f"❌ 签到失败，HTTP 状态码：{resp.status_code}")
    except Exception as e:
        add_message(f"❌ 签到请求异常：{e}")

def send_via_worker(message: str):
    """通过 Cloudflare Worker 转发消息到 Telegram"""
    if not (WORKER_DOMAIN and WORKER_KEY and TELEGRAM_CHAT_ID):
        print("⚠️ 缺少 DOMAIN、WORKER_KEY 或 TG_USER_ID，跳过推送。")
        return

    url = f"https://{WORKER_DOMAIN}/"
    payload = {
        "key": WORKER_KEY,
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code == 200:
            print("✅ 已通过 Worker 转发消息")
        else:
            print(f"❌ Worker 返回非 200：{r.status_code} {r.text}")
    except Exception as e:
        print(f"❌ 调用 Worker 异常：{e}")

def main():
    signin_rousi()
    # 如需延时可加 time.sleep()
    if final_messages:
        summary = "[rousi 签到结果]\n" + "\n".join(final_messages)
        send_via_worker(summary)

if __name__ == "__main__":
    main()

# 兼容 Serverless handler
def handler(event, context):
    main()
