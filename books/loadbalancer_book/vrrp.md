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

## VRRPの詳細な動作
VRRPでは、複数のロードバランサを一つの仮想的なロードバランサとしてみなし、クライアントがその仮想的なロードバランサにアクセスしようとすることで動作します。そのため、実際のロードバランサが持つものとは別に、仮想的なものであるVirtual IPアドレスとVirtual MACアドレスというものがあります。IPアドレスはネットワーク上における住所のようなものであり、MACアドレスは、機器が持つ固有の識別番号です。

以下の図のようなDocker上の構成においての動作を説明していきます。

![VRRPの動作](/images/VRRP/vrrp_failover.png)
*図3：VRRPの詳細な動作*

クライアントがVirtual IPアドレスにアクセスをする際、まず、どのロードバランサに接続するのかを確認することから始まります。このVitural IPアドレスから機器固有の識別番号であるVirtual MACアドレスを得るためにARPリクエストというものを送信します。ARPとは「Address Resolution Protocol」の略称であり、IPアドレスからMACアドレスに変換するためのプロトコルです。このAPRリクエストはVRRPの仕様上、MASTERコンテナが応答し、Docker Engineが仲介します。Docker Engineはスイッチのような動作を振る舞うのではと想定しています。
ARPリクエストを付け取ったMASTERコンテナは、その応答として自身のMACアドレスとVirtual MACアドレスをARPレスポンスとしてDocker Engineに流します。Docker EngineはMACアドレステーブルという形で、Vitual MACアドレスとロードバランサコンテナのMACアドレスの対応表を持ちます。アクセスが来た際には、このVirtual MACアドレスに対応するロードバランサにアクセスを振ることで対応します。
最終的にクライアントまでARPレスポンスであるVitual MACアドレスを返すことで、クライアントのARPリクエストを完了とします。これにより、Vitual IPアドレスにアクセスすることが可能となります。あくまで、クライアントに返ってくるMACアドレスはVirtual MACアドレスであるため、クライアントはがアクセスするロードバランサがMASTERコンテナなのかBACKUPコンテナなのかを意識するせずに通信することになります。
次に、実際にアクセスをしていきます。Vitural IPアドレスにアクセスすると、先ほど入手したVitural MACアドレス宛にリクエストを送ります。Docker Engineが仲介し、Vitural MACアドレスに対応するMACアドレスのロードバランサコンテナへアクセスを流します。そこからは、ロードバランサに設定された振り分け方式に従って、サーバコンテナにアクセスを振り分けます。応答したサーバからコンテンツが返ってきて、クライアントまで届けられます。

**フェイルオーバー**
VRRPの機能であるフェイルオーバー時はBACKUPコンテナがVirtual MACアドレスを引き継ぎ、応答するようになります。
まず、MASTERコンテナは定期的にVRRPアドバタイズメントという通信をBACKUPコンテナに送信しています。MASTERコンテナに障害が発生するとBACKUPコンテナにVRRPアドバタイズメントを送信することができなくなります。そのため、BACKPUコンテナ側は、MASTERコンテナから一定時間VRRPアドバタイズメントを受信できない場合、MASTERコンテナ側に障害が発生したと判断してMASTERコンテナに切り替わって処理を行うようになります。なお、BACKUPコンテナからMASTERコンテナへとVRRPアドバタイズメントを送信しないため、MASTERコンテナはBACKUPコンテナを認識することができません。
VRRPアドバタイズメントが途切れ、BACKUPコンテナがMASTERコンテナに障害が発生したと判断すると、Vitual MACアドレスを引き継ぎ、即座にGARPをDocker Engineに送信します。GARPとは「Gratuitous ARP」というARPパケットの一種であり、次の二つの役割を持つプロトコルです。
- 自分自身に設定するIPアドレスが重複していないかどうかを検出する
- 同一セグメントのネットワーク機器上のARPキャッシュを更新させる

このGARPをDocker Engineに送信することで、Docker Engineが持つMACアドレステーブルを書き換えます。もともとVitural MACアドレスには、MASTERコンテナのMACアドレスが対応していたが、クライアントからのリクエストがダウンしているMASTERコンテナに流れないようにBACKUPコンテナのMACアドレスに書き換えます。これにより、MASTERコンテナに障害が発生した際のフェイルオーバーが完了となります。

ダウンしたロードバランサの障害が解消し、復帰する際、BACKUPコンテナへのフェイルオーバー時と同様の形式でフェイルオーバーを行います。復帰するロードバランサに設定したpriorityが現在動作しているロードバランサのpriorityよりも高い場合、復帰するロードバランサがMASTERコンテナとして動作するために、GARPをDocker Engineに送信します。Vitural MACアドレスと動作するロードバランサのMACアドレスの対応を書き換え、クライアントからのリクエストを受け取れるようにします。復帰するロードバランサのpriorityが動作しているロードバランサのpriorityよりも低い場合は、そのままBACKUPコンテナとして復帰します。


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
- client
    - Dockerfile
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
clientコンテナから仮想ipアドレス`192.168.1.100`へcurlコマンドを用いたリクエストを送ってみましょう。
`docker desktop`の画面のコンテナにある`Exec`での入力
または
```sh
docker exec -it vrrp-client-1 bash
```
で該当のコンテナに入力ができます

``` client.sh
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

この結果よりclientからの`curl`リクエストが各サーバにラウンドロビン方式で分散されていることが確認できます

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
