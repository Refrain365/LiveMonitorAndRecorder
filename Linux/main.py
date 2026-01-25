import sys
import os
import time
import subprocess
import logging
import argparse
from config import ConfigManager
from monitor import LiveMonitor

# --- 后台进程入口 ---
if len(sys.argv) > 1 and '--daemon' in sys.argv:
    parser = argparse.ArgumentParser()
    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--mode', type=str, default='all')
    args = parser.parse_args()

    # === 优化点 1: 更清晰的时间格式 ===
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',  # 加了方括号
        datefmt='%Y-%m-%d %H:%M:%S',         # 年-月-日 时:分:秒
        filename='monitor_daemon.log',
        filemode='a'
    )
    
    cfg = ConfigManager()
    monitor = LiveMonitor(cfg)
    monitor.run_check_loop(mode=args.mode)
    sys.exit(0)

# --- 交互界面 ---

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("="*40)
    print("   LiveMonitor Linux (CLI交互版)")
    print("="*40)

def get_non_empty_input(prompt):
    while True:
        value = input(prompt).strip()
        if value: return value
        print("❌ 输入不能为空！")

# --- 菜单逻辑 (Cookie 和 主播管理 部分保持不变，省略以节省篇幅) ---
# ... (请保留原有的 menu_cookies 和 menu_streamers 函数) ...

def menu_cookies(cfg):
    # (保持原有代码不变)
    while True:
        print_header()
        print("【1. 配置 Cookie & 全局设置】")
        print("-" * 30)
        print("1. 修改 Bilibili Cookie")
        print("2. 修改 抖音 Cookie")
        print("3. 修改 检测间隔 (当前: {}秒)".format(cfg.cookie_data['global_settings'].get('check_interval', 60)))
        print("0. 返回上级")
        print("-" * 30)
        
        c = input("请选择: ")
        if c == '0': break
        
        if c == '1':
            current = cfg.cookie_data['cookies'].get('bilibili', '')
            print(f"\n当前 B站 Cookie: {current[:20]}..." if current else "\n当前为空")
            val = input("请输入新Cookie (回车不改): ").strip()
            if val:
                cfg.cookie_data['cookies']['bilibili'] = val
                cfg.save_cookie_settings()
                print("✅ 保存成功")
        elif c == '2':
            current = cfg.cookie_data['cookies'].get('douyin', '')
            print(f"\n当前 抖音 Cookie: {current[:20]}..." if current else "\n当前为空")
            val = input("请输入新Cookie (回车不改): ").strip()
            if val:
                cfg.cookie_data['cookies']['douyin'] = val
                cfg.save_cookie_settings()
                print("✅ 保存成功")
        elif c == '3':
            val = input("请输入新的检测间隔(秒): ")
            if val.isdigit():
                cfg.cookie_data['global_settings']['check_interval'] = int(val)
                cfg.save_cookie_settings()
                print("✅ 保存成功")
        time.sleep(1)

def menu_streamers(cfg):
    # (保持原有代码不变)
    while True:
        print_header()
        print("【2. 主播管理】")
        print("-" * 30)
        print("1. 添加 Bilibili 主播")
        print("2. 添加 抖音 主播")
        print("3. 查看/删除 已有主播")
        print("0. 返回上级")
        print("-" * 30)
        
        c = input("请选择: ")
        if c == '0': break
        
        if c in ['1', '2']:
            is_bili = (c == '1')
            platform = 'bilibili' if is_bili else 'douyin'
            
            print(f"\n正在添加 [{platform}] 主播")
            name = get_non_empty_input("请输入主播昵称: ")
            
            print("\n请输入直播间链接:")
            if is_bili: print("✅ 示例: https://live.bilibili.com/123456")
            else: print("✅ 示例: https://live.douyin.com/123456 (请勿用短链)")
            
            url = get_non_empty_input("请输入链接: ")
            rec = input("\n是否自动录制? (y/n, 默认y): ").strip().lower()
            cfg.add_streamer(name, url, platform, rec != 'n')
            print(f"\n✅ 已添加: {name} 到 {platform}.json")
            time.sleep(1)
            
        elif c == '3':
            all_s = []
            bili_s = cfg.get_streamers('bilibili')
            douyin_s = cfg.get_streamers('douyin')
            for s in bili_s: s['_type'] = 'bilibili'
            for s in douyin_s: s['_type'] = 'douyin'
            all_s = bili_s + douyin_s
            
            if not all_s:
                print("\n暂无主播。")
                input("回车继续...")
                continue
                
            print(f"\n{'ID':<4} {'平台':<10} {'昵称':<15} {'自动录制'}")
            print("-" * 50)
            for idx, s in enumerate(all_s):
                print(f"{idx+1:<4} {s['_type']:<10} {s['name']:<15} {s.get('auto_record')}")
            
            print("-" * 50)
            d = input("输入序号删除主播 (回车返回): ")
            if d.isdigit():
                idx = int(d) - 1
                if 0 <= idx < len(all_s):
                    target = all_s[idx]
                    if target['_type'] == 'bilibili':
                        cfg.bili_list.remove(target)
                    else:
                        cfg.douyin_list.remove(target)
                    cfg.save_streamers()
                    print(f"🗑️ 已删除: {target['name']}")
                    time.sleep(1)

def menu_start():
    print_header()
    print("【3. 启动监听】")
    print("-" * 30)
    print("1. 🚀 启动 - 监控 [所有主播]")
    print("2. 🚀 启动 - 仅监控 [Bilibili]")
    print("3. 🚀 启动 - 仅监控 [抖音]")
    print("4. 🛑 暂停/停止 后台服务")
    print("5. 📜 查看 实时日志")
    print("0. 返回")
    print("-" * 30)
    
    c = input("请选择: ")
    mode = None
    if c == '1': mode = 'all'
    elif c == '2': mode = 'bilibili'
    elif c == '3': mode = 'douyin'
    
    if mode:
        os.system("pkill -f 'monitor_daemon.log' || true")
        
        if getattr(sys, 'frozen', False):
            args = [sys.executable, "--daemon", "--mode", mode]
        else:
            args = [sys.executable, __file__, "--daemon", "--mode", mode]
            
        with open('monitor_daemon.log', 'a') as log_file:
            subprocess.Popen(args, stdout=log_file, stderr=log_file, start_new_session=True)
            
        print(f"\n🚀 已启动后台服务 (模式: {mode})")
        print("您可以直接关闭本窗口，录制不会停止。")
        input("按回车返回...")
        
    elif c == '4':
        print("\n正在停止监控主程序...")
        
        # === 优化点 2: 主动写入停止日志 ===
        # 在杀进程之前，先往日志里写一句，确保留痕
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            with open('monitor_daemon.log', 'a') as f:
                f.write(f"[{timestamp}] ⏸️ 用户请求暂停/停止服务...\n")
        except:
            pass
            
        os.system("pkill -f 'monitor_daemon.log'")
        
        print("⚠️  提示：正在进行的录制任务需要单独确认。")
        kill_all = input("❓ 是否强制终止所有录制(Streamlink/FFmpeg)? (y/n): ").lower()
        if kill_all == 'y':
            os.system("pkill -f streamlink")
            os.system("pkill -f ffmpeg")
            print("✅ 已强制清理所有进程。")
        else:
            print("✅ 监控已停，录制继续。")
        time.sleep(2)
        
    elif c == '5':
        print("\n正在查看日志 (Ctrl+C 退出)...")
        time.sleep(1)
        try: os.system("tail -f monitor_daemon.log")
        except: pass

def main():
    cfg = ConfigManager()
    while True:
        print_header()
        print("1. 配置 Cookie & 全局设置")
        print("2. 添加/管理 主播")
        print("3. 开始监听 (后台模式)")
        print("0. 退出程序")
        print("-" * 40)
        choice = input("请输入选项: ")
        if choice == '1': menu_cookies(cfg)
        elif choice == '2': menu_streamers(cfg)
        elif choice == '3': menu_start()
        elif choice == '0': sys.exit()

if __name__ == "__main__":
    main()
