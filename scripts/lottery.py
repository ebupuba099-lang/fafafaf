#!/usr/bin/env python3
"""获取排列3/排列5开奖号码，更新仓库数据"""
import json
import os
import base64
import requests
from datetime import datetime

GH_TOKEN = os.environ.get('GH_TOKEN', '')
REPO = 'ebupuba099-lang/fafafaf'
DATA_FILE = 'data/lottery_data.json'

# 体彩官方API
SPORTTERY_API = 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=350133&provinceId=0&pageSize=1&is11=0'
# 灰鸟备用API
HUINIAO_API = 'http://api.huiniao.top/interface/home/lotteryHistory?type=plw&page=1&limit=1'

def load_data():
    """从仓库加载当前数据"""
    headers = {'Authorization': f'token {GH_TOKEN}', 'Accept': 'application/vnd.github.v3.raw'}
    resp = requests.get(f'https://api.github.com/repos/{REPO}/contents/{DATA_FILE}', headers=headers)
    resp.raise_for_status()
    return resp.json()

def save_data(data):
    """保存数据到仓库"""
    headers = {'Authorization': f'token {GH_TOKEN}', 'Accept': 'application/vnd.github.v3+json'}
    sha_resp = requests.get(f'https://api.github.com/repos/{REPO}/contents/{DATA_FILE}', headers=headers)
    sha_resp.raise_for_status()
    sha = sha_resp.json()['sha']
    
    content = json.dumps(data, ensure_ascii=False)
    b64 = base64.b64encode(content.encode('utf-8')).decode()
    
    put_resp = requests.put(
        f'https://api.github.com/repos/{REPO}/contents/{DATA_FILE}',
        headers=headers,
        json={
            'message': 'auto: update lottery results',
            'content': b64,
            'sha': sha
        }
    )
    put_resp.raise_for_status()
    print(f"Data saved to repo: {DATA_FILE}")

def fetch_winning_number():
    """从体彩API获取最新开奖号码"""
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
    
    for table_id, table in data.get('tablePages', {}).items():
        records = table.get('records', [])
        current_period = 0
        if records:
            current_period = records[-1].get('period', 0) + 1
        
        new_record = {
            'period': current_period,
            'winning': winning4,
            'results': None
        }
        records.append(new_record)
        table['records'] = records
    
    data['lastUpdate'] = int(datetime.now().timestamp() * 1000)
    
    save_data(data)
    print(f"Lottery results updated: {winning4}")

if __name__ == '__main__':
    main()
