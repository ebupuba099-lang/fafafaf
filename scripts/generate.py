#!/usr/bin/env python3
"""生成新一期递减序列并更新Gist和仓库数据文件"""
import json
import os
import random
import requests
from datetime import datetime, timedelta

GIST_ID = os.environ.get('GIST_ID', 'd32d11b8ed886ed36b2d2cf57e693e54')
GH_TOKEN = os.environ.get('GH_TOKEN', '')
GIST_FILENAME = 'lottery_data.json'
DATA_FILE = 'data/lottery_data.json'

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
    print("Gist updated successfully")

def save_to_repo(data):
    """保存数据到仓库文件"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Repo data file updated: {DATA_FILE}")

def generate_decreasing_sequence():
    """生成0-9的随机排列并递减"""
    digits = list(range(10))
    random.shuffle(digits)
    full = ''.join(str(d) for d in digits)
    
    sequences = [full]
    current = full
    while len(current) > 1:
        # 随机移除一个数字
        idx = random.randint(0, len(current) - 1)
        current = current[:idx] + current[idx+1:]
        sequences.append(current)
    return sequences

def generate_touweihe(sequences_qian, sequences_ge):
    """生成头尾合序列"""
    # 头尾合 = 千位头 + 个位头 的数字之和
    touweihe = []
    for i in range(min(len(sequences_qian), len(sequences_ge))):
        qian_head = int(sequences_qian[i][0]) if sequences_qian[i] else 0
        ge_head = int(sequences_ge[i][0]) if sequences_ge[i] else 0
        touweihe.append(str(qian_head + ge_head))
    
    full = ''.join(touweihe)
    seqs = [full]
    current = full
    while len(current) > 1:
        idx = random.randint(0, len(current) - 1)
        current = current[:idx] + current[idx+1:]
        seqs.append(current)
    return seqs

def main():
    data = load_data()
    
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    
    # 为每个工具生成新序列
    for tool_id, tool in data.get('toolPages', {}).items():
        qian = generate_decreasing_sequence()
        bai = generate_decreasing_sequence()
        shi = generate_decreasing_sequence()
        ge = generate_decreasing_sequence()
        touweihe = generate_touweihe(qian, ge)
        
        tool['result'] = {
            '千': qian,
            '百': bai,
            '十': shi,
            '个': ge,
            '头尾合': touweihe
        }
        # Update basePeriod and baseDate to today
        tool['baseDate'] = today_str
        # Calculate current period
        current_period = tool.get('basePeriod', 2026136)
        # Keep the period advancing
        tool['basePeriod'] = current_period
    
    data['lastUpdate'] = int(datetime.now().timestamp() * 1000)
    
    save_to_gist(data)
    save_to_repo(data)
    print("Generation complete!")

if __name__ == '__main__':
    main()
