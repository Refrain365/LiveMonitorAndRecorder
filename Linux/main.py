import sys, os, time, subprocess, logging, argparse, signal, shutil
from config import ConfigManager

if len(sys.argv) > 1 and '--daemon' in sys.argv:
    parser = argparse.ArgumentParser()
    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--mode', type=str, default='all')
    args, _ = parser.parse_known_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', filename='monitor_daemon.log', filemode='a')
    from monitor import LiveMonitor
    LiveMonitor(ConfigManager()).run_check_loop(mode=args.mode)
    sys.exit(0)

def graceful_exit(signum=None, frame=None):
    print("\n\n\033[1;32m ✅ 程序已安全退出！\033[0m")
    time.sleep(0.5); os.system('clear'); os._exit(0)

signal.signal(signal.SIGINT, graceful_exit)

def get_width(text):
    """精准计算中英文混合字符串的显示宽度"""
    width = 0
    for char in text:
        if ord(char) > 127: width += 2
        else: width += 1
    return width

def pad_text(text, target_width):
    """补齐空格以达到目标宽度，解决中文对齐问题"""
    cur_w = get_width(text)
    return text + " " * (target_width - cur_w)

def header():
    os.system('clear')
    try:
        t, u, f = shutil.disk_usage("/")
        p = (u/t)*100
        d_color = "\033[1;31m" if p > 90 else "\033[1;34m"
        disk_info = f"{d_color}磁盘状态: {f/(1024**3):.1f}GB 剩余 ({p:.1f}% 已使用)\033[0m"
    except: disk_info = ""
    
    # 斜体风格的 ASCII Art 标题
    print("\033[1;36m")
    print(r"    __    _             __  ___            _ _             ")
    print(r"   / /   (_)   _____   /  |/  /___  ____  (_) /_____  _____")
    print(r"  / /   / / | / / _ \ / /|_/ / __ \/ __ \/ / __/ __ \/ ___/")
    print(r" / /___/ /| |/ /  __// /  / / /_/ / / / / / /_/ /_/ / /    ")
    print(r"/_____/_/ |___/\___//_/  /_/\____/_/ /_/_/\__/\____/_/     ")
    print("\033[0m")
    print("-" * 68)
    print(f"{disk_info.center(68)}")
    print("-" * 68 + "\n")

def menu_config(cfg):
    while True:
        header()
        gs = cfg.cookie_data['global_settings']
        print("\033[1;33m【 1. 全 局 配 置 中 心 】\033[0m\n")
        print(" 1. B站 Cookie 设置")
        print(" 2. 抖音 Cookie 设置")
        print(f" 3. 检测间隔 (当前: {gs['check_interval']}s)")
        print(f" 4. 录制分段 (当前: {gs.get('split_size', 0)} GB)")
        print(" 5. WxPusher AppToken")
        print(" 6. 添加 WxPusher UID")
        print(" 7. 清空所有推送 UID")
        print("\n 0. 返回主菜单\n")
        c = input("选择选项: ").strip()
        if c == '0': break
        try:
            if c == '4':
                v = input("\n分段大小(GB, 0为不分): ").strip()
                if v: gs['split_size'] = float(v)
            elif c in ['1','2','3','5','6','7']:
                if c == '7': cfg.cookie_data['notification']['wxpusher_uids'] = []
                else:
                    val = input("\n输入新值 (直接回车取消): ").strip()
                    if val:
                        if c == '1': cfg.cookie_data['cookies']['bilibili'] = val
                        elif c == '2': cfg.cookie_data['cookies']['douyin'] = val
                        elif c == '3': gs['check_interval'] = int(val)
                        elif c == '5': cfg.cookie_data['notification']['wxpusher_app_token'] = val
                        elif c == '6': cfg.cookie_data['notification']['wxpusher_uids'].append(val)
            cfg.save_cookie_settings(); print("✅ 已更新")
        except: print("❌ 输入有误")
        time.sleep(0.8)

def menu_streamers(cfg):
    while True:
        header()
        streamers = cfg.get_streamers()
        mon_on = os.system("ps aux | grep 'main.py --daemon' | grep -v grep > /dev/null") == 0
        print("\033[1;33m【 2. 主 播 管 理 后 台 】\033[0m\n")
        # 严格计算宽度的表头
        print(f" {'ID':<6}{pad_text('昵称', 22)}{pad_text('平台', 12)}{'当前状态'}")
        print(" " + "-" * 62)
        
        for i, s in enumerate(streamers):
            p_url = s['url'].split('?')[0]
            if not mon_on:
                status_ui = "\033[37m○ 未监控\033[0m"
            else:
                is_rec = os.system(f"ps aux | grep streamlink | grep 'REC_ID:{p_url}' | grep -v grep > /dev/null") == 0
                status_ui = "\033[1;31m🔴 录制中\033[0m" if is_rec else "\033[1;32m● 监控中\033[0m"
            
            # 使用列表对齐函数
            row = f" {i+1:<6}{pad_text(s['name'], 22)}{pad_text(s['platform'], 12)}{status_ui}"
            print(row)
            
        print(" " + "-" * 62 + "\n")
        print(" b. 添加 B站主播")
        print(" d. 添加 抖音主播")
        print(" q. 修改录制画质")
        print(" x. 删除主播 (强制停止)")
        print("\n 0. 返回主菜单\n")
        c = input("操作: ").lower().strip()
        if c == '0': break
        try:
            if c == 'b' or c == 'd':
                name, url = input("昵称: ").strip(), input("链接: ").strip()
                if name and url: cfg.add_streamer(name, url, 'bilibili' if c=='b' else 'douyin')
            elif c == 'q':
                idx = int(input("主播 ID: ")) - 1
                q = input("画质(best/1080p): ").strip()
                if q: streamers[idx]['quality'] = q; cfg.save_streamers()
            elif c == 'x':
                idx = int(input("删除 ID: ")) - 1
                s = streamers[idx]
                if input(f"❗ 确定删除 {s['name']}? (y/n): ").lower() == 'y':
                    os.system(f"pkill -9 -f 'REC_ID:{s['url'].split('?')[0]}'")
                    if s['platform'] == 'bilibili': cfg.bili_list.remove(s)
                    else: cfg.douyin_list.remove(s)
                    cfg.save_streamers()
        except: print("⚠️ 操作有误")
        time.sleep(1)

def menu_service():
    while True:
        header()
        mon_on = os.system("ps aux | grep 'main.py --daemon' | grep -v grep > /dev/null") == 0
        notif_on = os.system("ps aux | grep 'notifier.py' | grep -v grep > /dev/null") == 0
        print("\033[1;33m【 3. 推 送 & 监 控 录 制 后 台 设 置 】\033[0m\n")
        print(f" 1. 推送后台服务: {'🟢 运行中' if notif_on else '🔴 已停止'}")
        print(f" 2. 监控录制后台: {'🟢 运行中' if mon_on else '🔴 已停止'}\n")
        print("-" * 35)
        print(" s1. 🚀 启动 [推送后台]")
        print(" s2. 🚀 启动 [监控任务]")
        print(" stop. 🛑 停止 [所有后台服务]")
        print(" re. 🔄 重启 [所有服务逻辑]")
        print(" l1. 📜 查看监控日志")
        print(" l2. 📜 查看推送日志")
        print("\n 0. 返回主菜单\n")
        c = input("指令: ").lower().strip()
        if c == '0': break
        if c == 's1': subprocess.Popen([sys.executable, "notifier.py"], start_new_session=True)
        elif c == 's2': subprocess.Popen([sys.executable, __file__, "--daemon", "--mode", "all"], start_new_session=True)
        elif c == 'stop':
            os.system("pkill -9 -f 'monitor_daemon.log' || true")
            os.system("pkill -9 -f 'main.py --daemon' || true")
            os.system("pkill -9 -f 'notifier.py' || true")
            if input("同步杀掉录制进程? (y/n): ").lower() == 'y': os.system("pkill -9 -f streamlink || true")
        elif c == 'l1': os.system("tail -f monitor_daemon.log")
        elif c == 'l2': os.system("tail -f notifier_daemon.log")
        time.sleep(0.8)

def main():
    cfg = ConfigManager()
    while True:
        header()
        print(" 1. 配置中心 (Cookie/推送/分段)")
        print(" 2. 主播管理 (添加/删除/对齐看板)")
        print(" 3. 推送 & 监控录制后台设置")
        print("\n 0. 退出程序")
        choice = input("\n请选择序号: ").strip()
        if choice == '1': menu_config(cfg)
        elif choice == '2': menu_streamers(cfg)
        elif choice == '3': menu_service()
        elif choice == '0': graceful_exit()

if __name__ == "__main__":
    main()
