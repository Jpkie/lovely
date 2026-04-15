"""
测试 SFTP API 端点
"""
import requests
import json

API_BASE = "http://127.0.0.1:3001/api/v1"

def test_api():
    print("=" * 60)
    print("测试 SFTP API 端点")
    print("=" * 60)
    
    # 1. 测试连接状态
    print("\n1. 测试 SSH 连接状态...")
    try:
        response = requests.get(f"{API_BASE}/ssh/connection-status", timeout=5)
        print(f"   状态码：{response.status_code}")
        print(f"   响应：{response.json()}")
    except requests.exceptions.ConnectionError:
        print("   [ERROR] 无法连接到后端 API")
        print("   请确保 Python 后端正在运行：cd src-python && python run.py")
        return False
    except Exception as e:
        print(f"   [ERROR] {e}")
        return False
    
    # 2. 测试列出文件 (需要先连接 SSH)
    print("\n2. 测试 SFTP 列出文件...")
    try:
        response = requests.post(f"{API_BASE}/sftp/list-files", params={"path": "/"}, timeout=5)
        print(f"   状态码：{response.status_code}")
        if response.status_code == 200:
            files = response.json()
            print(f"   [OK] 找到 {len(files)} 个文件")
            for f in files[:5]:
                icon = "[DIR]" if f.get('is_dir') else "[FILE]"
                print(f"   {icon} {f.get('name', 'unknown')}")
        else:
            print(f"   [ERROR] {response.text}")
    except Exception as e:
        print(f"   [ERROR] {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_api()
