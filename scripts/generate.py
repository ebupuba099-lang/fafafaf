#!/usr/bin/env python3
"""生成新一期递减序列，更新toolPages + 为每个表格添加新期记录"""
import json
import os
import random
import base64
import requests
from datetime import datetime

GH_TOKEN = os.environ.get('GH_TOKEN', '')
REPO = 'ebupuba099-lang/fafafaf'
DATA_FILE = 'data/lottery_data.json'

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
        json={'message': 'auto: generate new period data', 'content': b64, 'sha': sha}
    )
    put_resp.raise_for_status()
    print(f"Data saved to repo")

def generate_decreasing_sequence():
    digits = list(range(10))
    random.shuffle(digits)
    full = ''.join(str(d) for d in digits)
    sequences = [full]
    current = full
    while len(current) > 1:
        idx = random.randint(0, len(current) - 1)
        current = current[:idx] + current[idx+1:]
        sequences.append(current)
    return sequences

def generate_touweihe(sequences_qian, sequences_ge):
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
    
    # 计算当天期数
    base_date = datetime(2026, 5, 11)  # 2026121对应2026-05-11
    days_diff = (today - base_date).days
    today_period = 2026121 + days_diff
    
    print(f"Today: {today_str}, Period: {today_period}")
    
    # 更新toolPages
    for tool_id, tool in data.get('toolPages', {}).items():
        qian = generate_decreasing_sequence()
        bai = generate_decreasing_sequence()
        shi = generate_decreasing_sequence()
        ge = generate_decreasing_sequence()
        touweihe = generate_touweihe(qian, ge)
        
        tool['result'] = {
            '千': qian, '百': bai, '十': shi, '个': ge, '头尾合': touweihe
        }
        tool['baseDate'] = today_str
        tool['basePeriod'] = today_period
    
    # 为每个表格添加新期记录（如果还没有的话）
    for table_id, table in data.get('tablePages', {}).items():
        records = table.get('records', [])
        name = table.get('name', tool.get('name', ''))
        
        # 检查是否已有今天期数的记录
        has_today = any(r.get('period') == today_period for r in records)
        if not has_today:
            # 生成序列
            qian = generate_decreasing_sequence()
            bai = generate_decreasing_sequence()
            shi = generate_decreasing_sequence()
            ge = generate_decreasing_sequence()
            touweihe = generate_touweihe(qian, ge)
            
            new_rec = {
                'period': today_period,
                'header': name,
                'sequences': {'千': qian, '百': bai, '十': shi, '个': ge, '头尾合': touweihe},
                'winning': ''  # 留空，等lottery.py填入
            }
            records.insert(0, new_rec)
            print(f"  添加 {name} {today_period}期记录")
        else:
            print(f"  {name} 已有{today_period}期记录，跳过")
        
        # 限制最多保留20条
        if len(records) > 20:
            table['records'] = records[:20]
        
        table['records'] = records
    
    data['lastUpdate'] = int(datetime.now().timestamp() * 1000)
    
    save_data(data)
    print("Generation complete!")

if __name__ == '__main__':
    main()
