#!/usr/bin/env python3
"""fafafaf - 抓取开奖结果并填入所有表格页"""
import json, os, ssl, sys, time, subprocess, urllib.request, urllib.error

# ========== 配置 ==========
DATA_FILE = "data/lottery_data.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")

API_SPORTTERY = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=350133&provinceId=0&pageSize=10&is11=0"
API_HUINIAO = "https://api.huiniao.top/interface/home/lotteryHistory?type=plw&page=1&limit=10"
API_CJCP = "https://www.cjcp.com.cn/ajax/lottery/history?lotteryId=85&pageSize=10&pageNo=1"
API_JCJ = "https://www.lottery.gov.cn/api/lottery_kj_detail_new.jspx?_ltype=4&_term="

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.lottery.gov.cn/",
}

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ========== 数据操作 ==========
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tablePages": {}, "lastUpdate": 0}

def save_data(data):
    data["lastUpdate"] = int(time.time() * 1000)
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def commit_to_github(message):
    if not REPO or not GH_TOKEN:
        print("无GH_TOKEN，跳过提交")
        return False
    try:
        repo_url = f"https://x-access-token:{GH_TOKEN}@github.com/{REPO}.git"
        subprocess.run(["git", "config", "user.name", "发财就手Bot"], check=True)
        subprocess.run(["git", "config", "user.email", "bot@facaijiushou.local"], check=True)
        subprocess.run(["git", "pull", "--rebase", repo_url, "main"], check=True, capture_output=True)
        subprocess.run(["git", "add", DATA_FILE], check=True)
        result = subprocess.run(["git", "commit", "-m", message], capture_output=True)
        if b"nothing to commit" in result.stdout + result.stderr:
            print("无变更，跳过提交")
            return False
        subprocess.run(["git", "push", repo_url, "main"], check=True)
        print(f"已提交: {message}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git操作失败: {e}")
        return False

# ========== HTTP 请求 ==========
def _request(url, timeout=15):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"  请求失败(第{attempt+1}次): {e}")
            if attempt < 2:
                time.sleep(2)
    return None

# ========== 多源抓取 ==========
def fetch_draws():
    """从4个API抓取最近多期开奖号码，返回 {完整期号: 5位号码} 映射"""

    # 1. 灰鸟API
    print("尝试灰鸟API...")
    result = _request(API_HUINIAO)
    if result:
        try:
            data = result.get("data", {})
            draws = {}
            items = data.get("list", []) or data.get("data", {}).get("list", [])
            for item in items:
                code = str(item.get("code", ""))
                number = (item.get("one", "") + item.get("two", "") +
                          item.get("three", "") + item.get("four", "") +
                          item.get("five", ""))
                if code and number and len(number) >= 5:
                    # 灰鸟的code格式可能是 "2026166" 或 "26166"
                    period = code if len(code) >= 7 else ("202" + code if len(code) <= 5 else code)
                    draws[period] = number
            if not draws:
                last = data.get("last", {})
                if last:
                    code = str(last.get("code", ""))
                    number = (last.get("one", "") + last.get("two", "") +
                              last.get("three", "") + last.get("four", "") +
                              last.get("five", ""))
                    if code and number and len(number) >= 5:
                        period = code if len(code) >= 7 else ("202" + code if len(code) <= 5 else code)
                        draws[period] = number
            if draws:
                print(f"  灰鸟API成功: {len(draws)}期")
                return draws
        except Exception as e:
            print(f"  灰鸟API解析失败: {e}")

    # 2. 体彩官方API
    print("尝试体彩官方API...")
    result = _request(API_SPORTTERY)
    if result:
        try:
            draws = {}
            items = result.get("value", {}).get("list", [])
            for item in items:
                period = str(item.get("lotteryDrawNum", ""))
                number = item.get("lotteryDrawResult", "").replace(" ", "")
                if period and number and len(number) >= 5:
                    draws[period] = number
            if draws:
                print(f"  体彩API成功: {len(draws)}期")
                return draws
        except Exception as e:
            print(f"  体彩API解析失败: {e}")

    # 3. 彩经网API
    print("尝试彩经网API...")
    result = _request(API_CJCP)
    if result:
        try:
            draws = {}
            items = result.get("data", {}).get("list", [])
            for item in items:
                period = str(item.get("issue", ""))
                number = str(item.get("drawCode", "")).replace(",", "").replace(" ", "")
                if period and number and len(number) >= 5:
                    draws[period] = number
            if draws:
                print(f"  彩经网API成功: {len(draws)}期")
                return draws
        except Exception as e:
            print(f"  彩经网API解析失败: {e}")

    # 4. 体彩官网新版API（逐个期号查询）
    print("尝试体彩官网新版API...")
    try:
        for test_period in range(2026167, 2026156, -1):
            url = API_JCJ + str(test_period)
            result = _request(url, timeout=10)
            if result and isinstance(result, dict):
                number = str(result.get("lotteryDrawResult", "") or result.get("drawNumber", "")).replace(" ", "")
                period = str(result.get("lotteryDrawNum", "") or result.get("termNum", ""))
                if period and number and len(number) >= 5:
                    print(f"  官网API成功: 1期")
                    return {period: number}
    except Exception as e:
        print(f"  官网API失败: {e}")

    return {}

# ========== 粒数计算 ==========
def calculate_hit(levels, draw_digit):
    """开奖数字最后出现在第几级，该级剩余个数=粒数"""
    if not levels or draw_digit not in levels[0]:
        return 0
    last_level = 0
    for i in range(len(levels)):
        if draw_digit in levels[i]:
            last_level = i
        else:
            break
    return len(levels[last_level])

def fill_record(record, front_four):
    """填入开奖号码并计算粒数（千/百/十/个 + 头尾合）"""
    record["winning"] = front_four
    seqs = record.get("sequences", {})
    pos_map = {"千": 0, "百": 1, "十": 2, "个": 3}
    hits = {}
    for pos, idx in pos_map.items():
        levels = seqs.get(pos, [])
        if levels:
            draw_digit = int(front_four[idx])
            hits[pos] = calculate_hit(levels, draw_digit)
    # 头尾合 = (千位 + 个位) % 10
    head_tail_sum = (int(front_four[0]) + int(front_four[3])) % 10
    ht_levels = seqs.get("头尾合", [])
    if ht_levels:
        hits["头尾合"] = calculate_hit(ht_levels, head_tail_sum)
    record["hits"] = hits
    return hits

# ========== 主流程 ==========
def main():
    data = load_data()
    table_pages = data.get("tablePages", {})
    if not table_pages:
        print("没有表格页数据")
        return

    total_updated = 0

    # 收集所有需要填入的期号（取第一个表格的 records 作为参考）
    first_page = list(table_pages.values())[0]
    first_records = first_page.get("records", [])
    pending_periods = sorted(set(
        str(r["period"]) for r in first_records if not r.get("winning")
    ))
    if not pending_periods:
        print("所有表格页的期号都已填入开奖号码，无需抓取")
        return

    print(f"待填入期号: {', '.join(pending_periods)}")

    # 抓取开奖数据
    draws = fetch_draws()
    if not draws:
        print(f"所有API均失败！待填入: {', '.join(pending_periods)}")
        if GH_TOKEN:
            print("GitHub Actions 环境，4个API全部失败")
        else:
            print("本地环境，请手动运行: python scripts/lottery.py")
        return

    print(f"获取到开奖数据: {sorted(draws.keys())}")
    draw_map = {str(k): v for k, v in draws.items()}

    # 遍历所有表格页，填入开奖号码
    for page_id, page in table_pages.items():
        page_name = page.get("name", page_id)
        records = page.get("records", [])
        page_updated = 0
        for record in records:
            period = str(record.get("period", ""))
            if record.get("winning"):
                continue  # 已填过
            if period not in draw_map:
                continue  # 这期还没开奖

            number = draw_map[period]
            front_four = number[:4]
            hits = fill_record(record, front_four)
            page_updated += 1
            total_updated += 1
            print(f"  [{page_name}] {period}期: 开奖{front_four}, 粒数{hits}")

    # 检查是否还有未填的
    still_pending = []
    for page_id, page in table_pages.items():
        for r in page.get("records", []):
            if not r.get("winning"):
                p = str(r.get("period", ""))
                if p not in still_pending:
                    still_pending.append(p)
    if still_pending:
        print(f"仍有{len(still_pending)}期未填入: {', '.join(sorted(still_pending))}")

    if total_updated == 0:
        print("没有需要更新的记录")
        return

    save_data(data)

    if not GH_TOKEN:
        # 本地环境：git add/commit/push
        try:
            subprocess.run(["git", "add", DATA_FILE], check=True)
            msg = f"auto: fill winning for {total_updated} records"
            result = subprocess.run(["git", "commit", "-m", msg], capture_output=True)
            if b"nothing to commit" not in result.stdout + result.stderr:
                subprocess.run(["git", "push"], check=True)
                print(f"已提交: {msg}")
        except subprocess.CalledProcessError as e:
            print(f"Git操作失败: {e}")
    else:
        commit_to_github(f"auto: fill winning for {total_updated} records across {len(table_pages)} tables")

if __name__ == "__main__":
    main()
