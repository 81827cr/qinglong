import os
import re
import time
import random
import cloudscraper  # <- 用它替代 requests

# 环境变量
SCHOOL_COOKIE    = os.environ.get('SCHOOL', '').strip()
TELEGRAM_CHAT_ID = os.environ.get('TG_USER_ID', '').strip()
WORKER_DOMAIN    = os.environ.get('DOMAIN', '').strip()
WORKER_KEY       = os.environ.get('WORKER_KEY', '').strip()

# 浏览器标头（注入登录态 Cookie）
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.6778.205 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate",  # requests 默认
    "Connection":      "keep-alive",
    "Referer":         "https://pt.btschool.club/index.php",
    "Cookie":          SCHOOL_COOKIE
}

final_messages = []

def add_message(msg: str):
    print(msg)
    final_messages.append(msg)

# 创建 cloudscraper 会话
scraper = cloudscraper.create_scraper()

def signin_school():
    """在 pt.btschool.club 执行签到，通过 Cloudflare JS 验证"""
    if not SCHOOL_COOKIE:
        add_message("❌ 未检测到 SCHOOL 环境变量（Cookie），请检查。")
        return

    # 随机延迟：模拟真实用户行为
    time.sleep(random.uniform(5, 60))

    # 1) 先 GET 首页，通过 JS Challenge 拿到验证 Cookie
    try:
        resp_index = scraper.get("https://pt.btschool.club/index.php",
                                 headers=HEADERS, timeout=10)
        if resp_index.status_code != 200:
            add_message(f"⚠️ 首页请求异常，状态码：{resp_index.status_code}")
    except Exception as e:
        add_message(f"⚠️ 首页请求出错：{e}")

    # 短暂停顿
    time.sleep(random.uniform(1, 5))

    # 2) 真正的签到请求
    try:
        url = "https://pt.btschool.club/index.php?action=addbonus"
        resp = scraper.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            m = re.search(r'<div[^>]*class=["\']text-success[^>]*>(.*?)</div>',
                          resp.text, re.S)
            if m:
                add_message(f"✅ 签到成功：{m.group(1).strip()}")
            else:
                add_message("✅ 签到完成，但未匹配到提示信息。")
        else:
            add_message(f"❌ 签到失败，HTTP 状态码：{resp.status_code}")
    except Exception as e:
        add_message(f"❌ 签到请求异常：{e}")

def send_via_worker(message: str):
    """通过 Cloudflare Worker 转发消息到 Telegram"""
    if not (WORKER_DOMAIN and WORKER_KEY and TELEGRAM_CHAT_ID):
        print("⚠️ 缺少 DOMAIN、WORKER_KEY 或 TG_USER_ID，跳过推送。")
        return

    try:
        r = scraper.post(f"https://{WORKER_DOMAIN}/",
                         json={"key": WORKER_KEY,
                               "chat_id": TELEGRAM_CHAT_ID,
                               "text": message},
                         timeout=5)
        if r.status_code == 200:
            print("✅ 已通过 Worker 转发消息")
        else:
            print(f"❌ Worker 返回非 200：{r.status_code} {r.text}")
    except Exception as e:
        print(f"❌ 调用 Worker 异常：{e}")

def main():
    signin_school()
    if final_messages:
        summary = "[school 签到结果]\n" + "\n".join(final_messages)
        send_via_worker(summary)

if __name__ == "__main__":
    main()

# 兼容 Serverless
def handler(event, context):
    main()
