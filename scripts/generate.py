#!/usr/bin/env python3
"""生成新一期9级递减序列，为每个表格添加新期记录"""
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
        json={'message': 'auto: generate new period', 'content': b64, 'sha': sha}
    )
    put_resp.raise_for_status()
    print("Data saved to repo")

def generate_decreasing_sequence():
    """0-9随机去掉1个，剩下9个随机排列，再逐级递减到1个，共9级"""
    digits = list(range(10))
    random.shuffle(digits)
    selected = digits[:9]  # 取9个
    sequences = [''.join(str(d) for d in selected)]
    current = list(selected)
    while len(current) > 1:
        idx = random.randint(0, len(current) - 1)
        current.pop(idx)
        sequences.append(''.join(str(d) for d in current))
    return sequences

def generate_touweihe(seq_qian, seq_ge):
    """头尾合：千位头+个位头 的和"""
    touweihe = []
    for i in range(min(len(seq_qian), len(seq_ge))):
        q = int(seq_qian[i][0]) if seq_qian[i] else 0
        g = int(seq_ge[i][0]) if seq_ge[i] else 0
        touweihe.append(str((q + g) % 10))
    full = ''.join(touweihe)
    seqs = [full]
    current = list(full)
    while len(current) > 1:
        idx = random.randint(0, len(current) - 1)
        current.pop(idx)
        seqs.append(''.join(current))
    return seqs

def main():
    data = load_data()
    
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    base_date = datetime(2026, 5, 11)
    days_diff = (today - base_date).days
    today_period = 2026121 + days_diff
    
    print(f"Today: {today_str}, Period: {today_period}")
    
    # 为每个表格添加新期记录
    for table_id, table in data.get('tablePages', {}).items():
        records = table.get('records', [])
        name = table.get('name', '?')
        
        has_today = any(r.get('period') == today_period for r in records)
        if not has_today:
            qian = generate_decreasing_sequence()
            bai = generate_decreasing_sequence()
            shi = generate_decreasing_sequence()
            ge = generate_decreasing_sequence()
            touweihe = generate_touweihe(qian, ge)
            
            new_rec = {
                'period': today_period,
                'header': name,
                'sequences': {'千': qian, '百': bai, '十': shi, '个': ge, '头尾合': touweihe},
                'winning': ''
            }
            records.insert(0, new_rec)
            print(f"  添加 {name} {today_period}期 (9级序列)")
        else:
            print(f"  {name} 已有{today_period}期，跳过")
        
        # 最多保留20条
        if len(records) > 20:
            table['records'] = records[:20]
    
    # 清理toolPages（如果还存在）
    if 'toolPages' in data:
        del data['toolPages']
    
    data['lastUpdate'] = int(today.timestamp() * 1000)
    save_data(data)
    print("Generation complete!")

if __name__ == '__main__':
    main()
