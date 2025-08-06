import os
import re
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# —— 环境变量 —— #
# 登录后从浏览器复制出的整个 Cookie 字符串（如 "uid=xxx; pass=xxx; ..."）
SCHOOL_COOKIE = os.environ.get('SCHOOL', '').strip()
# 用于 Telegram 推送
TELEGRAM_CHAT_ID = os.environ.get('TG_USER_ID', '').strip()
WORKER_DOMAIN   = os.environ.get('DOMAIN', '').strip()
WORKER_KEY      = os.environ.get('WORKER_KEY', '').strip()

def add_message(msg, out_list):
    print(msg)
    out_list.append(msg)

def send_via_worker(message: str):
    """通过 Cloudflare Worker 转发消息到 Telegram"""
    import requests
    if not (WORKER_DOMAIN and WORKER_KEY and TELEGRAM_CHAT_ID):
        print("⚠️ 缺少 DOMAIN、WORKER_KEY 或 TG_USER_ID，跳过推送。")
        return

    try:
        r = requests.post(
            f"https://{WORKER_DOMAIN}/",
            json={"key": WORKER_KEY, "chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=5
        )
        if r.status_code == 200:
            print("✅ 已通过 Worker 转发消息")
        else:
            print(f"❌ Worker 返回非 200：{r.status_code} {r.text}")
    except Exception as e:
        print(f"❌ 调用 Worker 异常：{e}")

def signin_school():
    """在 pt.btschool.club 执行签到，绕过 Cloudflare JS Challenge"""
    final_msgs = []

    if not SCHOOL_COOKIE:
        add_message("❌ 未检测到 SCHOOL 环境变量（Cookie），请检查。", final_msgs)
        return final_msgs

    # 1) 随机延迟 5–60s
    time.sleep(random.uniform(5, 60))

    # 2) 启动 Chrome 无头浏览器
    opts = uc.ChromeOptions()
    opts.headless = True
    # 可选：设置窗口大小模拟真实
    opts.add_argument("--window-size=1440,900")
    driver = uc.Chrome(options=opts)

    try:
        # 3) 访问首页，触发 CF JS Challenge
        driver.get("https://pt.btschool.club/index.php")
        # 等待 CF 验证完成（通常 5–7 秒）
        time.sleep(random.uniform(7, 9))

        # 4) 注入登录态 Cookie（若站点仍需登录校验）
        #    请把 SCHOOL_COOKIE 按 "k=v; k2=v2" 格式复制
        for pair in SCHOOL_COOKIE.split(';'):
            if '=' in pair:
                name, val = pair.strip().split('=', 1)
                driver.add_cookie({
                    'name': name, 'value': val,
                    'domain': 'pt.btschool.club', 'path': '/'
                })
        # 刷新使 Cookie 生效
        driver.refresh()
        time.sleep(random.uniform(1, 3))

        # 5) 签到
        driver.get("https://pt.btschool.club/index.php?action=addbonus")
        time.sleep(random.uniform(2, 4))

        html = driver.page_source
        m = re.search(r'<div[^>]*class=["\']text-success[^>]*>(.*?)</div>', html, re.S)
        if m:
            add_message(f"✅ 签到成功：{m.group(1).strip()}", final_msgs)
        else:
            add_message("❌ 未匹配到签到提示，可能已签到或页面变化。", final_msgs)

    except Exception as e:
        add_message(f"❌ 签到过程出错：{e}", final_msgs)

    finally:
        driver.quit()

    return final_msgs

def main():
    msgs = signin_school()
    if msgs:
        summary = "[school 签到结果]\n" + "\n".join(msgs)
        send_via_worker(summary)

if __name__ == "__main__":
    main()

# Serverless handler 兼容
def handler(event, context):
    main()
