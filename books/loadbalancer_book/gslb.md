---
title: "広域負荷分散（GSLB）システムの構築"
---

## GSLBとは
GSLB（Global Server Load Balancing）は、地理的に分散した複数のデータセンター間でトラフィックを分散させる技術です。DNSを利用して、ユーザーからのアクセスを最適なサーバーに誘導します。

通常の負荷分散が同一施設内のサーバー間で行われるのに対し、GSLBはリージョンを跨いだ広域的な負荷分散を実現します。これにより、災害対策、パフォーマンス最適化、地域特化サービスの提供が可能になります。

## GSLB技術要素

本記事では、GSLBシステムの核となるDNS制御機能、ヘルスチェック機能、負荷分散アルゴリズムの3つの技術要素について紹介します。これらは組み合わせて使用することで、効果的なGSLBシステムを構築できます。

### DNS制御機能
GSLBの基盤となる技術です。ローカルDNSからリクエストされるDNSクエリに対して、GSLB装置で応答するIPアドレスをコントロールすることで広域負荷分散を実現します。 具体的には、ユーザーがwww.example.comにアクセスする際、DNS応答で東京サーバー、大阪サーバー、米国サーバーのうち最適なものを返します。
![DNS制御機能の挙動](https://scrapbox.io/files/68cffcf9401e2672aebd1219.png)
*図1: DNS制御機能の挙動*

#### メリット・デメリット
メリットは、既存のDNSインフラを活用でき、実装が容易な点です。また、クライアント側に追加設定が不要で透明性が高いです。
デメリットは、DNSキャッシュによる切り替え遅延です。TTLの設定により迅速な切り替えとDNS負荷のトレードオフが発生します。また、単純なDNS応答のため、リアルタイムなサーバー状態を反映しにくいです。

#### 応用例
このDNSベース方式には様々な応用が可能です。
例えば、「地理的DNS分散」があります。これは通常のDNSベース方式に加えて、クライアントの地理的位置に基づいて最適なサーバーに誘導するものです。主にGeoIPデータベースを活用し、日本からのアクセスは東京データセンター、米国からのアクセスは米国データセンターに誘導することで地理的最適化を実現します。

### ヘルスチェック方式
定義されたロジックに基づいて、地理的に分散したデータセンターの間で最適なトラフィック誘導を行うアルゴリズムです。 各サーバーの稼働状況、応答時間、負荷状況を定期的に監視し、健全なサーバーのみをDNS応答に含めます。 正常時には東京DCに配置されたサーバにトラフィックを転送して、東京DCの障害発生時に大阪DCのサーバにトラフィックを転送するような動作を行います。
![ヘルスチェック機能の挙動](https://scrapbox.io/files/68cffd558df2189d658adfb4.png)
*図2: ヘルスチェック機能の挙動*

#### メリット・デメリット
可用性の向上が見込めるのがメリットです。実際のサーバー状態に基づく判断が可能で、重大なリソース障害が発生した場合のシームレスなフェイルオーバーとフェイルバックを提供します。
デメリットは、ヘルスチェック機能の実装と運用が複雑になることです。また、ヘルスチェック間隔とフェイルオーバー速度のバランス調整が必要で、誤検知による不要な切り替えリスクもあります。

### 負荷分散アルゴリズム
ユーザーに最適なサーバーを選択するためのアルゴリズムです。 地理的位置、サーバー負荷、応答時間などの要素を組み合わせて最適なサーバーを決定します。 主な手法には、GeoIPベースの地理的分散、ラウンドロビン、重み付け分散などがあります。
![負荷分散アルゴリズムの挙動](https://scrapbox.io/files/68cffd7e78a10ed94d67c1e4.png)
*図3:負荷分散アルゴリズムの挙動*


#### メリット・デメリット
メリットは、多様な条件を組み合わせた柔軟な分散制御が可能なことです。ユーザー体験の最適化と効率的なリソース活用を実現できます。
デメリットは、アルゴリズムが複雑になると判断処理に時間がかかることです。また、最適化の条件設定により、予期しない負荷偏りが発生するリスクがあります。

## 演習
IPMininetを用いて実際にGSLBシステムを構築し、各技術要素の動作を検証します。
配布しているファイルを用いて、各広域負荷分散方式を実装できるように構成されています。
仕組みは以下の通りです。
1. IPMininetでBGPルーティング対応の仮想ネットワークを構築します。
2. BIND9 DNSサーバーでビュー機能を設定し、地域別の応答を実現します。
3. ヘルスチェッカーが定期的にサーバー状態を監視します。
4. 障害検知時にゾーンファイルを自動更新してrndcでリロードします。
5. 各地域のクライアントが地理的に最適なサーバーIPを受信します。
6. BGPによる経路制御でサーバー間の通信を実現します。

実装の環境は仮想ネットワーク上で再現します。
構成としては以下の通りです。
```
gslb.py（ネットワークトポロジー）
dns_configs/
├── named.conf.options
├── named.conf.local  
├── db.service.example.jp
├── db.service.example.us
├── db.service.example.jp.template
├── db.service.example.us.template
└── db.root
health_checker.py
frr_gslb_configs/
├── bg_jp.conf
├── bg_us.conf
├── global1.conf
├── global2.conf
├── r1.conf
└── r2.conf
```

### コードファイルの入手

本演習で使用するコードファイルは以下から入手できます：

- [GitHubリポジトリ](https://github.com/prmn2024-infla-network/loadbalancer_book/tree/main/code/gslb)
- [ZIPダウンロード](https://github.com/prmn2024-infla-network/loadbalancer_book/archive/refs/heads/main.zip)

ZIPをダウンロード後、`code/gslb/` ディレクトリ内のファイルをご利用ください。

ネットワーク図は以下の通りです。
![ネットワーク図](https://scrapbox.io/files/68cffc98832b26ed7b3d7e3f.png)
*図4:ネットワーク図*

各ファイルの役割は以下のとおりです。
### メインファイル
#### gslb.py
役割: ネットワークトポロジーの構築と初期設定

- IPMininetでBGPルーティング対応ネットワークを作成
- 3つのAS（200:日本、201:米国、100:グローバル）を定義
- ルータ、サーバー、クライアントの配置
- BGP設定ファイルの配布とサービス起動
- BIND9とヘルスチェッカーの自動起動
#### health_checker.py
役割: サーバー監視と自動フェイルオーバー

- 5秒間隔でWebサーバーの死活監視
- 障害検知時のDNSゾーンファイル自動更新
- 地域別優先順位に基づくサーバー選択
- BIND9への設定反映（rndc reload）

### DNS設定ファイル群
#### named.conf.local
役割: 地理的DNS分散の中核設定

- ACL定義：jp-clients (192.168.1.0/24), us-clients (192.168.2.0/24)
- ビュー定義：jp-view（日本向け）, us-view（米国向け）
- 各ビューでの異なるゾーンファイル指定

#### named.conf.options
役割: BIND9サーバーの基本設定

- 動作ディレクトリ：/var/cache/bind
- 待ち受けアドレス：127.0.0.1, 192.168.1.100
- 再帰問い合わせの許可設定

### ゾーンファイル群
#### db.service.example.jp
役割: 日本クライアント向けの実際のDNS応答データ
```
　www     IN      A       10.0.1.10  # 日本サーバー優先
```
#### db.service.example.us
役割: 米国クライアント向けの実際のDNS応答データ
```
　www     IN      A       10.0.2.10  # 米国サーバー優先
```
#### db.service.example.jp.template
役割: 日本ビュー用の動的更新テンプレート

- @SERIAL@: タイムスタンプで自動更新
- @WWW_A_RECORDS@: health_checker.pyが動的に置換

#### db.service.example.us.template
役割: 米国ビュー用の動的更新テンプレート

- 同様のプレースホルダー構造

#### db.root
役割: ルートDNSサーバー情報

- インターネットのルートネームサーバー一覧
- 再帰問い合わせ時に使用

### BGP設定ファイル群
#### r1.conf, r2.conf
役割: エッジルータの設定

- クライアント側ルータ（AS200, AS201）
- クライアントネットワークの広告
- 上位BGPルータとのiBGP接続

#### bg_jp.conf, bg_us.conf
役割: 地域BGPルータの設定

- AS間接続の中継点
- eBGP/iBGPピアリング設定
- 経路の再配布

#### global1.conf, global2.conf
役割: サーバー側BGPルータの設定

- Webサーバーへの接続
- サーバーネットワーク（10.0.1.0/24, 10.0.2.0/24）の広告
- AS100内のiBGP設定

実行手順は、ネットワークを起動し、DNSサーバーとヘルスチェッカーを開始することで実行できます。
実行結果は、各クライアントからのDNS問い合わせで確認可能です。

### 演習1: 基本動作確認
実際にネットワークを起動して構築したGSLBが機能しているか検証しましょう。
```
 ###### 1. ネットワーク起動
 sudo python3 gslb.py
 
 ###### 2. 初期DNS応答確認
   mininet> client1 dig www.service.example
  
  ; <<>> DiG 9.16.1-Ubuntu <<>> www.service.example
  ;; global options: +cmd
  ;; Got answer:
  ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 50151
  ;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
  
  ;; OPT PSEUDOSECTION:
  ; EDNS: version: 0, flags:; udp: 4096
  ; COOKIE: 320aacf8a4d619570100000068cff7cbaab42e8b5cd8cec3 (good)
  ;; QUESTION SECTION:
  ;www.service.example.           IN      A
  
  ;; ANSWER SECTION:
  www.service.example.    60      IN      A       10.0.1.10　　#server1
  
  ;; Query time: 0 msec
  ;; SERVER: 192.168.1.100#53(192.168.1.100)
  ;; WHEN: Sun Sep 21 13:04:11 UTC 2025
  ;; MSG SIZE  rcvd: 92
  
  ##### 3. 初期DNS応答確認
  mininet> client2 dig www.service.example
   
   ; <<>> DiG 9.16.1-Ubuntu <<>> www.service.example
   ;; global options: +cmd
   ;; Got answer:
   ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 5404
   ;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
   
   ;; OPT PSEUDOSECTION:
   ; EDNS: version: 0, flags:; udp: 4096
   ; COOKIE: b9e6ba190e2926850100000068cff7d446e47cb45e4e4266 (good)
   ;; QUESTION SECTION:
   ;www.service.example.           IN      A
   
   ;; ANSWER SECTION: 
   www.service.example.    60      IN      A       10.0.2.10  #server2
   
   ;; Query time: 4 msec
   ;; SERVER: 192.168.1.100#53(192.168.1.100)
   ;; WHEN: Sun Sep 21 13:04:20 UTC 2025
   ;; MSG SIZE  rcvd: 92
```

この結果よりGSLBが機能していることが確認できました。

### 演習2:ヘルスチェック機能の検証
構築したGSLBのヘルスチェック機能の検証を行いましょう。
```
 ##### 1. server1を停止してフェイルオーバーテスト
 mininet> server1 pkill -f "python3 -m http.server"
 
 ##### 2. 15秒待機（ヘルスチェック動作待ち）
 mininet> gslb_dns bash -c "sleep 15"
 
 ##### 3. DNS応答の変化確認（フェイルオーバー）
 mininet> client1 dig www.service.example
 
 ; <<>> DiG 9.16.1-Ubuntu <<>> www.service.example
 ;; global options: +cmd
 ;; Got answer:
 ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 19818
 ;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
 
 ;; OPT PSEUDOSECTION:
 ; EDNS: version: 0, flags:; udp: 4096
 ; COOKIE: f03920c4d6fb67740100000068cfafc8e68a3213a66b0cd0 (good)
 ;; QUESTION SECTION:
 ;www.service.example.           IN      A
 
 ;; ANSWER SECTION:
 www.service.example.    60      IN      A       10.0.2.10  # server1→server2にフェイルオーバー
 
 ;; Query time: 0 msec
 ;; SERVER: 192.168.1.100#53(192.168.1.100)
 ;; WHEN: Sun Sep 21 07:56:56 UTC 2025
 ;; MSG SIZE  rcvd: 92
 
 #4. DNS応答が変化していないことの確認
 mininet> client2 dig www.service.example
 
 ; <<>> DiG 9.16.1-Ubuntu <<>> www.service.example
 ;; global options: +cmd
 ;; Got answer:
 ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 35337
 ;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
 
 ;; OPT PSEUDOSECTION:
 ; EDNS: version: 0, flags:; udp: 4096
 ; COOKIE: fc87935ba775c2ef0100000068cfafce4c119c0efd4e0211 (good)
 ;; QUESTION SECTION:
 ;www.service.example.           IN      A
 
 ;; ANSWER SECTION:
 www.service.example.    60      IN      A       10.0.2.10　　#変化なし
 
 ;; Query time: 0 msec
 ;; SERVER: 192.168.1.100#53(192.168.1.100)
 ;; WHEN: Sun Sep 21 07:57:02 UTC 2025
 ;; MSG SIZE  rcvd: 92
```

この結果よりserver1がダウンした事によりヘルスチェック機能からserver2へとフェイルオーバーができていることが確認できました。

## まとめ
本記事では、以下の3種類の広域負荷分散技術要素について、実装例とともに解説しました。

- DNS制御機能:シンプルで実装が容易。既存インフラを活用可能。
- ヘルスチェック機能:高可用性とフェイルオーバー機能を提供。
- 負荷分散アルゴリズム:地理的最適化によるパフォーマンス向上。

それぞれの特性を理解し、用途やシステム要件に応じて適切な構成を選択することが重要です。

