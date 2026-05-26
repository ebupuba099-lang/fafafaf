#!/usr/bin/env python3
"""获取排列3/排列5开奖号码，更新数据"""
import json
import os
import requests
from datetime import datetime

GIST_ID = os.environ.get('GIST_ID', 'd32d11b8ed886ed36b2d2cf57e693e54')
GH_TOKEN = os.environ.get('GH_TOKEN', '')
GIST_FILENAME = 'lottery_data.json'
DATA_FILE = 'data/lottery_data.json'

# 体彩官方API
SPORTTERY_API = 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=350133&provinceId=0&pageSize=1&is11=0'
# 灰鸟备用API
HUINIAO_API = 'http://api.huiniao.top/interface/home/lotteryHistory?type=plw&page=1&limit=1'

def load_data():
    """从Gist加载数据"""
    headers = {'Authorization': f'token {GH_TOKEN}'}
    resp = requests.get(f'https://api.github.com/gists/{GIST_ID}', headers=headers)
    resp.raise_for_status()
    content = resp.json()['files'][GIST_FILENAME]['content']
    return json.loads(content)

def save_to_gist(data):
    """保存数据到Gist"""
    headers = {
        'Authorization': f'token {GH_TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {
        'files': {
            GIST_FILENAME: {
                'content': json.dumps(data, ensure_ascii=False)
            }
        }
    }
    resp = requests.patch(f'https://api.github.com/gists/{GIST_ID}', headers=headers, json=payload)
    resp.raise_for_status()

def save_to_repo(data):
    """保存数据到仓库文件"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_winning_number():
    """从体彩API获取最新开奖号码"""
    # 先尝试官方API
    try:
        resp = requests.get(SPORTTERY_API, timeout=10)
        data = resp.json()
        if data.get('value') and data['value'].get('list'):
            latest = data['value']['list'][0]
            lotteryNum = latest.get('lotteryNum', '')
            # 排列3取前3位，排列5取前5位（我们取前4位用于千/百/十/个）
            return lotteryNum[:4], lotteryNum
    except Exception as e:
        print(f"Official API failed: {e}")
    
    # 备用API
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
    
    # 更新每个表格页的开奖记录
    for table_id, table in data.get('tablePages', {}).items():
        records = table.get('records', [])
        # 计算当前期数
        current_period = 0
        if records:
            current_period = records[-1].get('period', 0) + 1
        
        # 添加新记录
        new_record = {
            'period': current_period,
            'winning': winning4,
            'results': None  # 结果在页面端计算
        }
        records.append(new_record)
        table['records'] = records
    
    data['lastUpdate'] = int(datetime.now().timestamp() * 1000)
    
    save_to_gist(data)
    save_to_repo(data)
    print(f"Lottery results updated: {winning4}")

if __name__ == '__main__':
    main()
