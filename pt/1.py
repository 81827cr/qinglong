import os
import re
import requests
import time

# 环境变量
SCHOOL_COOKIE   = os.environ.get('SCHOOL', '').strip()
TELEGRAM_CHAT_ID = os.environ.get('TG_USER_ID', '').strip()
WORKER_DOMAIN   = os.environ.get('DOMAIN', '').strip()
WORKER_KEY      = os.environ.get('WORKER_KEY', '').strip()

# 完整请求头（建议直接用浏览器抓包的内容再替换 COOKIE 和 Referer）
HEADERS = {
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh-HK;q=0.8,zh;q=0.7,en-US;q=0.6,en;q=0.5',
    'Cookie': SCHOOL_COOKIE,           # 环境变量注入
    'Host': 'pt.btschool.club',
    'Referer': 'https://pt.btschool.club/index.php',  # 首页
    'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'Sec-Ch-Ua-Arch': '"x86"',
    'Sec-Ch-Ua-Bitness': '"64"',
    'Sec-Ch-Ua-Full-Version': '"131.0.6778.205"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Model': '""',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Ch-Ua-Platform-Version': '"19.0.0"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.6778.205 Safari/537.36'
    ),
}


final_messages = []

def add_message(msg: str):
    print(msg)
    final_messages.append(msg)

def signin_school():
    """在 pt.btschool.club 上执行签到"""
    if not SCHOOL_COOKIE:
        add_message("❌ 未检测到 SCHOOL 环境变量，请检查。")
        return

    url = "https://pt.btschool.club/index.php?action=addbonus"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            # 根据页面实际的提示 HTML 修改下面的正则
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
    """通过 POST 把消息和密钥发给 Cloudflare Worker"""
    if not WORKER_DOMAIN or not WORKER_KEY or not TELEGRAM_CHAT_ID:
        print("❌ 缺少 DOMAIN、WORKER_KEY 或 CHAT_ID")
        return

    url = f"https://{WORKER_DOMAIN}/"   # 只用根路径
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
            print("❌ Worker 返回非 200:", r.status_code, r.text)
    except Exception as e:
        print("❌ 调用 Worker 异常:", e)


def main():
    signin_school()
    # 如果需要延时，可自行加上 time.sleep()
    if final_messages:
        summary = "[btschool 签到结果]\n" + "\n".join(final_messages)
        send_via_worker(summary)

if __name__ == "__main__":
    main()

# 兼容 Serverless handler
def handler(event, context):
    main()
