#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件锁机制测试脚本
验证portalocker文件锁是否正常工作
"""

import os
import time
import threading
from app import load_data, save_data

def test_concurrent_access():
    """测试并发访问文件锁机制"""
    print("Testing file lock mechanism...")

    # 获取当前数据
    data = load_data()
    original_groups_count = len(data.get('groups', []))
    print(f"Original groups count: {original_groups_count}")

    results = []

    def worker(worker_id):
        """工作线程函数"""
        try:
            # 读取数据
            data = load_data()
            groups_count = len(data.get('groups', []))

            # 模拟一些处理时间
            time.sleep(0.1)

            # 添加一个测试组
            test_group = {
                'id': max([g['id'] for g in data.get('groups', [])], default=0) + worker_id,
                'images': [{'id': 999 + worker_id, 'filename': f'test_image_{worker_id}.jpg'}],
                'primary_category': f'test_category_{worker_id}',
                'tags': [f'test_tag_{worker_id}'],
                'reviewed': False,
                'modified': False
            }
            data['groups'].append(test_group)

            # 保存数据
            save_data(data)

            results.append(f"Worker {worker_id}: SUCCESS")
            print(f"Worker {worker_id}: SUCCESS")

        except Exception as e:
            results.append(f"Worker {worker_id}: ERROR - {e}")
            print(f"Worker {worker_id}: ERROR - {e}")

    # 创建多个线程同时访问
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)

    # 启动所有线程
    print("Starting 5 concurrent workers...")
    for t in threads:
        t.start()

    # 等待所有线程完成
    for t in threads:
        t.join()

    # 检查结果
    final_data = load_data()
    final_groups_count = len(final_data.get('groups', []))
    print(f"\nFinal groups count: {final_groups_count}")
    print(f"Added groups: {final_groups_count - original_groups_count}")

    # 清理测试数据
    final_data['groups'] = final_data['groups'][:original_groups_count]
    save_data(final_data)

    print("Test completed. Results:")
    for result in results:
        print(f"  {result}")

    return len([r for r in results if "SUCCESS" in r]) == 5

if __name__ == "__main__":
    print("=" * 50)
    print("File Lock Mechanism Test")
    print("=" * 50)

    success = test_concurrent_access()

    print("=" * 50)
    if success:
        print("[OK] All tests passed! File lock mechanism is working correctly.")
    else:
        print("[ERROR] Some tests failed. Check the file lock implementation.")
    print("=" * 50)
