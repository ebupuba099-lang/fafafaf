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
    try:
        resp = requests.get(SPORTTERY_API, timeout=10)
        data = resp.json()
        if data.get('value') and data['value'].get('list'):
            latest = data['value']['list'][0]
            lotteryNum = latest.get('lotteryNum', '')
            return lotteryNum[:4], lotteryNum
    except Exception as e:
        print(f"Official API failed: {e}")
    try:
        resp = requests.get(HUINIAO_API, timeout=10)
        data = resp.json()
        if data.get('data') and len(data['data']) > 0:
            latest = data['data'][0]
            number = latest.get('number', latest.get('lotteryNum', ''))
            return number[:4], number
    except Exception as e:
        print(f"Backup API failed: {e}")
    return None, None

def main():
    winning4, full_number = fetch_winning_number()
    if not winning4:
        print("Failed to fetch winning number, skipping")
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
                break
    
    if updated > 0:
        data['lastUpdate'] = int(datetime.now().timestamp() * 1000)
        # 清理toolPages
        if 'toolPages' in data:
            del data['toolPages']
        save_data(data)
        print(f"Updated {updated} tables, winning={winning4}")
    else:
        print("No empty winning records found")

if __name__ == '__main__':
    main()
