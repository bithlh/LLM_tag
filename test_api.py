import requests
import json

# 测试JSONL导出
print('=== 测试JSONL导出 ===')
r = requests.get('http://127.0.0.1:5000/api/export/jsonl')
lines = r.text.strip().split('\n')
print(f'总行数: {len(lines)}')

if lines:
    first_line = lines[0]
    print(f'第一行长度: {len(first_line)}')
    try:
        data = json.loads(first_line)
        print('JSON格式正确')
        print(f'包含字段: {list(data.keys())}')
        if 'output' in data:
            print(f'output字段包含: {list(data["output"].keys())}')
    except json.JSONDecodeError as e:
        print(f'JSON解析错误: {e}')

print('\n=== 测试单个组导出 ===')
r2 = requests.get('http://127.0.0.1:5000/api/export/single/5')
if r2.status_code == 200:
    print('单个组导出成功')
    data = r2.json()
    print(f'包含字段: {list(data.keys())}')
else:
    print(f'单个组导出失败: {r2.status_code}')
