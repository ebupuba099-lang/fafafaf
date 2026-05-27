#!/usr/bin/env python3
"""获取排列3/排列5开奖号码，填入winning为空的表格记录"""
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
    """尝试从多个API获取最新开奖号码，返回4位数字字符串"""
    # 方案1: 体育彩票官方API
    try:
        resp = requests.get(SPORTTERY_API, timeout=10)
        data = resp.json()
        if data.get('value') and data['value'].get('list'):
            latest = data['value']['list'][0]
            # 字段名是lotteryDrawResult，格式如 "4 6 6 2 3"
            result = latest.get('lotteryDrawResult', '')
            if result:
                digits = result.replace(' ', '')
                if len(digits) >= 4:
                    winning4 = digits[:4]
                    print(f"官方API获取成功: 期号={latest.get('lotteryDrawNum')}, 号码={result}, 取前4位={winning4}")
                    return winning4
    except Exception as e:
        print(f"官方API失败: {e}")

    # 方案2: 灰鸟API
    try:
        resp = requests.get(HUINIAO_API, timeout=10)
        data = resp.json()
        if data.get('data'):
            # data是dict, 含last和data.list
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
                if len(winning4) == 4 and winning4.isdigit():
                    print(f"灰鸟API获取成功: 期号={last.get('code')}, 号码={one}{two}{three}{four}{last.get('five','')}")
                    return winning4
    except Exception as e:
        print(f"灰鸟API失败: {e}")

    return None

def main():
    winning4 = fetch_winning_number()
    if not winning4:
        print("所有API均未获取到开奖号码，跳过")
        return

    data = load_data()
    updated = 0
    for table_id, table in data.get('tablePages', {}).items():
        records = table.get('records', [])
        for rec in records:
            if rec.get('winning', '') == '' or rec.get('winning') is None:
                rec['winning'] = winning4
                updated += 1
                print(f"  填入 {table.get('name','?')} 期{rec['period']} 开奖号={winning4}")
                break  # 每个表格只填一条空记录

    if updated > 0:
        data['lastUpdate'] = int(datetime.now().timestamp() * 1000)
        # 清理toolPages
        if 'toolPages' in data:
            del data['toolPages']
        save_data(data)
        print(f"共更新{updated}个表格, 开奖号={winning4}")
    else:
        print("没有空的winning记录需要填入")

if __name__ == '__main__':
    main()
