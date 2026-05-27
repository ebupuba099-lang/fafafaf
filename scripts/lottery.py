#!/usr/bin/env python3
"""获取排列3/排列5开奖号码，填入winning为空的表格记录（校验期号匹配）"""
import json
import os
import base64
import requests
from datetime import datetime

GH_TOKEN = os.environ.get('GH_TOKEN', '')
REPO = 'ebupuba099-lang/fafafaf'
DATA_FILE = 'data/lottery_data.json'

SPORTTERY_API = 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=350133&provinceId=0&pageSize=1&is11=0'
HUINIAO_API = 'http://api.huiniao.top/interface/home/lotteryHistory?type=plw&page=1&limit=1'

def load_data():
    headers = {'Authorization': f'token {GH_TOKEN}', 'Accept': 'application/vnd.github.v3.raw'}
    resp = requests.get(f'https://api.github.com/repos/{REPO}/contents/{DATA_FILE}', headers=headers)
    resp.raise_for_status()
    return resp.json()

def save_data(data):
    headers = {'Authorization': f'token {GH_TOKEN}', 'Accept': 'application/vnd.github.v3+json'}
    sha_resp = requests.get(f'https://api.github.com/repos/{REPO}/contents/{DATA_FILE}', headers=headers)
    sha_resp.raise_for_status()
    sha = sha_resp.json()['sha']
    content = json.dumps(data, ensure_ascii=False)
    b64 = base64.b64encode(content.encode('utf-8')).decode()
    put_resp = requests.put(
        f'https://api.github.com/repos/{REPO}/contents/{DATA_FILE}',
        headers=headers,
        json={'message': 'auto: update lottery results', 'content': b64, 'sha': sha}
    )
    put_resp.raise_for_status()

def fetch_winning_number():
    """尝试从多个API获取最新开奖号码，返回 (4位数字字符串, 期号数字) 或 (None, None)"""
    # 方案1: 体育彩票官方API
    try:
        resp = requests.get(SPORTTERY_API, timeout=10)
        data = resp.json()
        if data.get('value') and data['value'].get('list'):
            latest = data['value']['list'][0]
            # 字段名是lotteryDrawResult，格式如 "4 6 6 2 3"
            result = latest.get('lotteryDrawResult', '')
            draw_num = latest.get('lotteryDrawNum', '')  # 如 "26136"
            if result:
                digits = result.replace(' ', '')
                if len(digits) >= 4:
                    winning4 = digits[:4]
                    # 期号转换：26136 → 2026136
                    period = None
                    if draw_num:
                        period = int('20' + draw_num)
                    print(f"官方API获取成功: 期号={draw_num}(→{period}), 号码={result}, 取前4位={winning4}")
                    return winning4, period
    except Exception as e:
        print(f"官方API失败: {e}")

    # 方案2: 灰鸟API
    try:
        resp = requests.get(HUINIAO_API, timeout=10)
        data = resp.json()
        if data.get('data'):
            last = None
            if isinstance(data['data'], dict):
                last = data['data'].get('last')
                if not last and data['data'].get('data', {}).get('list'):
                    last = data['data']['data']['list'][0]
            elif isinstance(data['data'], list) and len(data['data']) > 0:
                last = data['data'][0]
            if last:
                one = last.get('one', '')
                two = last.get('two', '')
                three = last.get('three', '')
                four = last.get('four', '')
                winning4 = f"{one}{two}{three}{four}"
                code = last.get('code', '')  # 如 "26136"
                period = None
                if code:
                    period = int('20' + code)
                if len(winning4) == 4 and winning4.isdigit():
                    print(f"灰鸟API获取成功: 期号={code}(→{period}), 号码={one}{two}{three}{four}{last.get('five','')}")
                    return winning4, period
    except Exception as e:
        print(f"灰鸟API失败: {e}")

    return None, None

def main():
    winning4, api_period = fetch_winning_number()
    if not winning4:
        print("所有API均未获取到开奖号码，跳过")
        return

    data = load_data()
    updated = 0
    skipped = 0
    for table_id, table in data.get('tablePages', {}).items():
        records = table.get('records', [])
        for rec in records:
            if rec.get('winning', '') == '' or rec.get('winning') is None:
                rec_period = rec.get('period')
                # 校验期号：API返回的期号必须与空winning记录的期号匹配
                if api_period and rec_period != api_period:
                    print(f"  跳过 {table.get('name','?')} 期{rec_period}: API期号={api_period}不匹配")
                    skipped += 1
                    break
                rec['winning'] = winning4
                updated += 1
                print(f"  填入 {table.get('name','?')} 期{rec_period} 开奖号={winning4}")
                break  # 每个表格只填一条空记录

    if updated > 0:
        data['lastUpdate'] = int(datetime.now().timestamp() * 1000)
        if 'toolPages' in data:
            del data['toolPages']
        save_data(data)
        print(f"共更新{updated}个表格, 开奖号={winning4}")
    elif skipped > 0:
        print(f"期号不匹配，共跳过{skipped}个表格（API期号={api_period}，数据空winning期号不同）")
    else:
        print("没有空的winning记录需要填入")

if __name__ == '__main__':
    main()
