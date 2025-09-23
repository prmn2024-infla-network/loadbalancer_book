import subprocess
import time
import os
import datetime

# グローバル設定 
SERVERS = {
    "jp": "10.0.1.10",  # server1
    "us": "10.0.2.10",  # server2
}
ZONE_NAME = "service.example"
CHECK_INTERVAL = 5  # チェック間隔（秒）

# ターゲット設定
# 各ターゲットがどのビューに属し、どのファイルを更新するかを定義
TARGETS = [
    {
        "view_name": "jp-view",
        "zone_file": "/etc/bind/db.service.example.jp",
        "template_file": "/etc/bind/db.service.example.jp.template",
        "server_priority": [SERVERS["jp"], SERVERS["us"]], # 日本クライアント向けの優先順位
    },
    {
        "view_name": "us-view",
        "zone_file": "/etc/bind/db.service.example.us",
        "template_file": "/etc/bind/db.service.example.us.template",
        "server_priority": [SERVERS["us"], SERVERS["jp"]], # 米国クライアント向けの優先順位
    }
]

def log_message(level, message):
    #コンソールにタイムスタンプ付きでログを出力する
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def check_server(ip):
    #指定されたIPにcurlでアクセスし、成功(True)か失敗(False)を返す
    result = subprocess.run(
        ["curl", "-s", "--connect-timeout", "1", f"http://{ip}"],
        capture_output=True
    )
    return result.returncode == 0

def generate_new_zone_content(template_file, ip_to_serve):
    #テンプレートと提供すべき単一のIPから、新しいゾーンファイルの内容を生成する。
    #シリアル値も現在時刻から自動生成する。
    with open(template_file, 'r') as f:
        content = f.read()

    a_records = f"www    IN    A    {ip_to_serve}\n"
    serial = int(time.time())
    new_content = content.replace("@WWW_A_RECORDS@", a_records)
    new_content = new_content.replace("@SERIAL@", str(serial)) 

    return new_content
    
def update_and_reload(target):
    #ターゲットの状態を確認し、提供すべきIPを決定し、
    #必要であればゾーンファイルを更新してリロードする。
    
    #優先順位に従って、最初に利用可能だったサーバーIPを一つだけ選択する
    ip_to_serve = None
    for ip in target["server_priority"]:
        if check_server(ip):
            ip_to_serve = ip
            break #正常なサーバーが一つ見つかったら、ループを抜ける

    # どのサーバーも利用できない場合、フォールバックとして最初の優先サーバーを指す
    if ip_to_serve is None:
        ip_to_serve = target["server_priority"][0]
        log_message("WARNING", f"All servers are down for view '{target['view_name']}'. Falling back to primary {ip_to_serve}.")

    # 新しいゾーンファイルの内容を生成
    new_content = generate_new_zone_content(target["template_file"], ip_to_serve)

    # 既存のゾーンファイルと比較し、変更がなければ何もしない
    needs_update = True
    try:
        if os.path.exists(target["zone_file"]):
            with open(target["zone_file"], 'r') as f:
                # シリアル行を除いて比較する
                current_content_no_serial = "".join(line for line in f.read().splitlines() if "Serial" not in line)
                new_content_no_serial = "".join(line for line in new_content.splitlines() if "Serial" not in line)
                if current_content_no_serial == new_content_no_serial:
                    needs_update = False
    except IOError as e:
        log_message("ERROR", f"Could not read zone file {target['zone_file']}: {e}")

    if needs_update:
        log_message("INFO", f"Updating {target['zone_file']} for view '{target['view_name']}' to point to {ip_to_serve}")
        try:
            with open(target["zone_file"], 'w') as f:
                f.write(new_content)
        except IOError as e:
            log_message("ERROR", f"Could not write to zone file {target['zone_file']}: {e}")
            return

        # 正しいrndcコマンドでリロード
        log_message("INFO", f"Reloading zone '{ZONE_NAME}' in view '{target['view_name']}'...")
        cmd = ["rndc", "reload", ZONE_NAME, "IN", target['view_name']]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            log_message("INFO", f"Reload successful for view '{target['view_name']}'.")
        else:
            log_message("ERROR", f"Reload failed for view '{target['view_name']}': {result.stderr.strip()}")

def main():
    log_message("INFO", "Health Checker started. Performing initial check...")
    # 起動時に一度、全ターゲットを更新する
    for target_config in TARGETS:
        update_and_reload(target_config)
    log_message("INFO", "Initial check complete. Starting regular monitoring.")

    while True:
        time.sleep(CHECK_INTERVAL)
        # 定期的に全ターゲットをチェック
        for target_config in TARGETS:
            update_and_reload(target_config)

if __name__ == "__main__":
    main()
