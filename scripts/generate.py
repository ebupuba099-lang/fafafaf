#!/usr/bin/env python3
"""生成新一期递减序列并更新仓库数据文件"""
import json
import os
import random
import requests
from datetime import datetime, timedelta

GH_TOKEN = os.environ.get('GH_TOKEN', '')
REPO = 'ebupuba099-lang/fafafaf'
DATA_FILE = 'data/lottery_data.json'

def load_data():
    """从仓库加载当前数据"""
    headers = {'Authorization': f'token {GH_TOKEN}', 'Accept': 'application/vnd.github.v3.raw'}
    resp = requests.get(f'https://api.github.com/repos/{REPO}/contents/{DATA_FILE}', headers=headers)
    resp.raise_for_status()
    return resp.json()

def save_data(data):
    """保存数据到仓库（先获取SHA再PUT）"""
    headers = {'Authorization': f'token {GH_TOKEN}', 'Accept': 'application/vnd.github.v3+json'}
    # 获取当前文件SHA
    sha_resp = requests.get(f'https://api.github.com/repos/{REPO}/contents/{DATA_FILE}', headers=headers)
    sha_resp.raise_for_status()
    sha = sha_resp.json()['sha']
    
    content = json.dumps(data, ensure_ascii=False)
    encoded = content.encode('utf-8')
    import base64
    b64 = base64.b64encode(encoded).decode()
    
    put_resp = requests.put(
        f'https://api.github.com/repos/{REPO}/contents/{DATA_FILE}',
        headers=headers,
        json={
            'message': 'auto: generate new period data',
            'content': b64,
            'sha': sha
        }
    )
    put_resp.raise_for_status()
    print(f"Data saved to repo: {DATA_FILE}")

def generate_decreasing_sequence():
    """生成0-9的随机排列并递减"""
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
    """生成头尾合序列"""
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
        tool['baseDate'] = today_str
        current_period = tool.get('basePeriod', 2026136)
        tool['basePeriod'] = current_period
    
    data['lastUpdate'] = int(datetime.now().timestamp() * 1000)
    
    save_data(data)
    print("Generation complete!")

if __name__ == '__main__':
    main()
