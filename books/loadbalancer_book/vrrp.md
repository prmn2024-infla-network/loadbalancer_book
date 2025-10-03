---
title: "VRRPによる冗長化"
---

本記事では、VRRPを用いたロードバランサーの冗長化について紹介します。

## VRRP(Virtual Router Redundancy Protocol)
デフォルトゲートウェイの可用性を向上させるネットワークプロトコルです。
VRRPを利用することで物理的な複数のルータを一つの仮想的なルータとして扱うことができます。
仮想的なルータは、マスタールータとバックアップルータで構成されており、通常時に稼働しているマスタールーターに障害が発生した場合、バックアップルーターの一つが自動的にマスタールータに切り替わります。
障害が発生の有無はkeepalivedのデーモンを用いて各ルータの接続状態を確認することで実現している。

### メリット・デメリット
メリットは複数のルータで構成するため、一台故障しても自動的にルータが切り替わり通信が遮断されない点です。
デメリットは実際に通信を処理するマスタールーターは一台であるため、仮想的なルータ内での負荷分散はできないという点です。


![通常時](/images/VRRP/normal.png)
*図1：通常時のVRRPを用いたロードバランサーの挙動*

![障害発生時](/images/VRRP/abnormal.png)
*図2：障害が発生時のVRRPを用いたロードバランサーの挙動*

## 演習1
配布しているファイルを用いて、VRRPを用いたロードバランサーを実装できるように構成されています。

仕組みは以下の通りです。

1. ルータ、サーバを立てます
2. masterコンテナのルータがmaster状態となり、backupコンテナのルータがbackup状態となる
3. 仮想ipアドレスへのリクエストが、master状態のロードバランサーから各サーバに振り分けられ、レスポンスが返ってくる
4. マスタールーターをダウンさせるとバックアップルーターがmaster状態となる
5. 仮想ipアドレスへのリクエストが、master状態となったバックアップルーターから各サーバに振り分けられ、レスポンスが返ってくる。


実装の環境はDocker上で再現します。 構成としては
- docker-compose.yml
- nginx.conf
- keepalived
    - Dockerfile
    - master.conf
    - backup.conf
    - start_nginx.sh
    - stop_nginx.sh
- server1
    - Dockerfile
    - index.html
- server2
    - Dockerfile
    - index.html
- server3
    - Dockerfile
    - index.html

では、以上を構成したフォルダを作成してみましょう。

`docker-compose up -d --build`のコマンドを入力し、作成したフォルダのdockerコンテナが立ち上げてみましょう。
masterコンテナのロードバランサーがmaster状態で、backupコンテナのロードバランサーがbackup状態であることを確認しましょう。

- master
``` master.sh
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: Starting VRRP child process, pid=7
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: (VI_1) Entering BACKUP STATE (init)
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: Startup complete
2025-06-15 00:19:58 Sat Jun 14 15:19:58 2025: (VI_1) Entering MASTER STATE
```

- backup
``` backup.sh
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: Starting VRRP child process, pid=7
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: (VI_1) Entering BACKUP STATE (init)
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: Startup complete
```

## 演習2
masterコンテナとbackupコンテナの両方から仮想ipアドレス`192.168.1.100`へcurlコマンドを用いたリクエストを送ってみましょう。
`docker desktop`の画面のコンテナにある`Exec`での入力
または
```sh
docker exec -it vrrp-master-1 bash
```
で該当のコンテナに入力ができます

- master
``` master.sh
/ # curl 192.168.1.100
<html>
  <body>
    <h1>Server1 - This is from Server1!</h1>
  </body>
</html>
/ # curl 192.168.1.100
<html>
  <body>
    <h1>Server2 - This is from Server2!</h1>
  </body>
</html>
/ # curl 192.168.1.100
<html>
  <body>
    <h1>Server3 - This is from Server3!</h1>
  </body>
</html>
/ # curl 192.168.1.100
<html>
  <body>
    <h1>Server1 - This is from Server1!</h1>
  </body>
</html>
```

- backup
``` backup.sh
/ # curl 192.168.1.100
curl: (7) Failed to connect to 192.168.1.100 port 80 after 21066 ms: Could not connect to server
```

この結果よりmaster状態のmasterコンテナだけがアクティブな状態であることが確認できます

## 演習3
masterコンテナを停止させてbackupコンテナがmaster状態に昇格することを確認しましょう
`docker desktop`の画面から`master-1`のコンテナのstopボタンを押す
または
```sh
docker stop vrrp-master-1
```
コマンドで該当のコンテナを停止させます。

- master
``` master.sh
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: Starting VRRP child process, pid=7
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: (VI_1) Entering BACKUP STATE (init)
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: Startup complete
2025-06-15 00:19:58 Sat Jun 14 15:19:58 2025: (VI_1) Entering MASTER STATE
2025-06-15 00:33:32 Sat Jun 14 15:33:32 2025: Stopping
2025-06-15 00:33:33 Sat Jun 14 15:33:33 2025: Stopped
2025-06-15 00:33:33 Sat Jun 14 15:33:33 2025: Stopped Keepalived v2.3.1 (05/24,2024)
```

- backup
``` backup.sh
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: Starting VRRP child process, pid=7
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: (VI_1) Entering BACKUP STATE (init)
2025-06-15 00:19:55 Sat Jun 14 15:19:55 2025: Startup complete
2025-06-15 00:33:33 Sat Jun 14 15:33:33 2025: (VI_1) Entering MASTER STATE
```

## まとめ
本記事では、VRRPを用いたロードバランサーの冗長化について紹介しました。
VRRPを導入することで、ネットワークの可用性が向上し、障害発生時の影響を最小限に抑えることができます。
また、導入する際には、どのようなネットワーク環境に適用するのかを事前に検討し、適切な設定を行うことが重要です。
