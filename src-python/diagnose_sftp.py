"""
诊断 SFTP 连接问题
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ssh_connection_manager import SSHConnectionManager
from app.services.ssh_manager import SSHManager

async def diagnose_sftp_issue():
    """诊断 SFTP 问题"""
    print("=" * 60)
    print("LovelyERes SFTP 连接诊断工具")
    print("=" * 60)
    
    # 1. 检查 SSH 连接管理器
    print("\n1. 检查 SSH 连接管理器...")
    connection_manager = SSHConnectionManager()
    connections = connection_manager.load_connections()  # 不是异步方法
    print(f"   已保存的 SSH 连接数：{len(connections)}")
    
    if connections:
        print("\n   保存的连接:")
        for conn in connections:
            print(f"   - {conn.name}: {conn.username}@{conn.host}:{conn.port}")
    else:
        print("   [!] 没有保存的 SSH 连接，请先添加 SSH 连接")
        return False
    
    # 2. 测试 SSH 连接
    print("\n2. 测试 SSH 连接...")
    ssh_manager = SSHManager()
    
    # 使用第一个连接测试
    test_conn = connections[0]
    print(f"   尝试连接：{test_conn.username}@{test_conn.host}:{test_conn.port}")
    
    try:
        # 解密密码
        decrypted_password = await connection_manager.decrypt_password(test_conn.encrypted_password)
        
        await ssh_manager.connect(
            host=test_conn.host,
            port=test_conn.port,
            username=test_conn.username,
            password=decrypted_password,
        )
        print("   [OK] SSH 连接成功")
    except Exception as e:
        print(f"   [ERROR] SSH 连接失败：{e}")
        print("\n   建议:")
        print("   1. 检查 SSH 服务器是否运行")
        print("   2. 检查网络连接")
        print("   3. 验证用户名和密码是否正确")
        return False
    
    # 3. 测试 SFTP 功能
    print("\n3. 测试 SFTP 功能...")
    try:
        files = await ssh_manager.list_sftp_files("/")
        print(f"   [OK] SFTP 列表成功，找到 {len(files)} 个条目")
        print(f"\n   前 10 个条目:")
        for f in files[:10]:
            icon = "[DIR]" if f.is_dir else "[FILE]"
            print(f"   {icon} {f.name} ({f.file_type}, {f.size} bytes)")
    except Exception as e:
        print(f"   [ERROR] SFTP 列表失败：{e}")
        print("\n   可能的原因:")
        print("   1. SFTP 子系统未启用")
        print("   2. 用户没有读取目录的权限")
        print("   3. 路径不存在")
        await ssh_manager.disconnect()
        return False
    
    # 4. 测试文件读取
    print("\n4. 测试文件读取...")
    try:
        # 尝试读取 /etc/hostname 或 /etc/passwd
        test_files = ["/etc/hostname", "/etc/passwd"]
        for test_file in test_files:
            try:
                content = await ssh_manager.read_sftp_file(test_file)
                print(f"   [OK] 成功读取 {test_file} ({len(content)} bytes)")
                break
            except FileNotFoundError:
                continue
        else:
            print("   [!] 无法读取测试文件")
    except Exception as e:
        print(f"   [ERROR] 文件读取失败：{e}")
    
    # 5. 清理
    await ssh_manager.disconnect()
    print("\n5. 断开连接...")
    print("   [OK] 已断开连接")
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)
    print("\n总结:")
    print("[OK] SSH 连接正常")
    print("[OK] SFTP 功能正常")
    print("\n如果前端仍然报错，请检查:")
    print("1. Python 后端是否运行在 http://127.0.0.1:3001")
    print("2. 浏览器控制台是否有 CORS 错误")
    print("3. 网络请求是否被防火墙阻止")
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(diagnose_sftp_issue())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n诊断被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 诊断过程出错：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
