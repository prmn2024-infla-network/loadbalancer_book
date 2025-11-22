---
title: "AWSによる負荷分散"
---

## AWSでの負荷分散
本記事では、AWSを使用した負荷分散手法について紹介します。
AWSではElastic Load Balancing (ELB) というサービス名でロードバランサが提供されている。このサービスにはApplication Load Balancer (ALB)、Network Load Balancer (NLB)、Gateway Load Balancer (GWLB)という3種類のロードバランサがあります。
これは複数のアベイラビリティーゾーンにあるEC2インスタンスなどのターゲットに対して、受信したトラフィックを自動的に負荷分散させることができます。また、登録されているターゲットは常にモニタリングされているため、正常なターゲットのみトラフィックをルーティングすることが可能です。
また、トラフィックの量の変化にあわせて処理能力を自動スケーリングすることもできます。

![ELB](/images/aws/elb.png)
*図1:ELBのルーティング*

### Application Load Balancer (ALB)
HTTPやHTTPSのトラフィックに対応するロードバランサであり、OSI参照モデルの第 7 層であるアプリケーション層で機能します。
そのため、HTTPリクエストの負荷分散を行うのであれば、ALBの利用が推奨されています。
ルーティングが柔軟に行えるのが特徴で、HTTPリクエストの内容をもとにした分散が可能です。URLでのパスやHTTPヘッダなどを基準に分散先を選択して、アクセスを分散させます。例を挙げると、`https://example.com/api`と`https://example.com/admin`というのリクエストパスの違いなど。

### Network Load Balancer (NLB)
TCPやUDPのトラフィックに対応し、OSI参照モデルの第 4 層であるトランスポート層で機能します。
毎秒数百万のリクエストを処理が可能で突発的なアクセス上昇にも対応することができ、非常に高いパフォーマンスで低レイテンシを維持することが可能です。そのため、大量のアクセスが想定されるアプリケーションにおいては、NLBの利用が推奨されています。
ALBやGWLBと違いIPアドレスを固定することができるため、IPアドレスの指定しての運用が可能です。


### Gateway Load Balancer (GWLB)
OSI参照モデルの第 3 層であるネットワーク層で機能します。基本的にネットワーク層で機能するが、ネットワーク層のゲートウェイ機能とトランスポート層の負荷分散機能の両方を備えている。
ファイアウォール、侵入検知および防止システムといったサードパーティー仮想アプライアンスを簡単にデプロイ、スケーリング、管理することができます。
つまり、セキュリティ用の「中継器」みたいなものでファイアウォールやIDS/IPSなどの仮想セキュリティ機器を自動で分散・スケールすることが可能です。
インターネットゲートウェイ経由で入る全てのトラフィックはGWLBエンドポイントにルーティングされ、検査が行われます。これにより、不正な通信はここで止められ、安全な通信だけが中に進むことができます。

## 演習
実際にAWSを使用して実装してみましょう。
ここではNetwork Load Balancer(NLB)を実装します。

### EC2インスタンスを用意する
アクセスの分散先であるサーバであるインスタンスを3つ用意します。

:::details 解答例
実装例です。
実装の詳細は、環境や要件に応じて適宜調整してください。

EC2のインスタンスの項目における「インスタンスの起動」ボタンを押す。

![Nginx編集後画面](/images/aws/instance.png)
*図2:EC2インスタンス*

EC2インスタンスの起動情報は以下の通りで作成します。

- インスタンス名は任意
- OSイメージはDebian
- インスタンスタイプはt2.micro
- キーペアを作成
- ネットワーク設定はssh,http,httpsを許可

残りはデフォルトのままで設定します。
:::


### インスタンスの設定を行う
用意した3つのサーバにSSH接続を行い、Nginxをインストールします。
また、各サーバにアクセスした際に各サーバ名が表示されるようにします。

:::details 解答例
実装例です。
実装の詳細は、環境や要件に応じて適宜調整してください。

まずは、各サーバへのSSH接続をubuntu環境で行います。
先程作成し、ダウンロードされた`.pem`キーペアをSSHする階層に置いておきます。
インスタンス概要の接続のボタンを押し、SSHクライアントを開きます。
そこから、`ssh -i`から始まるコマンドをコピーして、実行します。
これにより、SSH接続が完了します。

**Nginxのインストール**

```sh
sudo apt update
sudo apt install nginx
```
を実行することでNginxのインストールが完了します。
この状態で`sudo systemctl start nginx`でNginxを起動して、ブラウザからアクセスを行うと、Nginxの初期画面が表示されます。

![Nginx初期画面](/images/aws/nginx_default.png)
*図3:Nginxの初期画面*

**サーバ名の表示に変更**
ブラウザ上に表示させるコードが書かれている`index.html`を探します。
まず、Nginxの設定ファイルを見つけます。
その中には`include /etc/nginx/sites-enabled/*;`のように書かれています。
そのため、`/etc/nginx/sites-enabled/`の中にある`default`を見てみると、`root /var/www/html;`と書かれており、このパスの先にブラウザで表示されていた画面のコードが記述されています。
実際に確認してみると、`index.nginx-debian.html`というファイルが存在し、ブラウザ上で表示されていた内容と同じものが記述されています。

```sh
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
html { color-scheme: light dark; }
body { width: 35em; margin: 0 auto;
font-family: Tahoma, Verdana, Arial, sans-serif; }
</style>
</head>
<body>
<h1>Welcome to nginx!</h1>
<p>If you see this page, the nginx web server is successfully installed and
working. Further configuration is required.</p>

<p>For online documentation and support please refer to
<a href="http://nginx.org/">nginx.org</a>.<br/>
Commercial support is available at
<a href="http://nginx.com/">nginx.com</a>.</p>

<p><em>Thank you for using nginx.</em></p>
</body>
</html>
```

このままでは編集の権限がないため、`sudo nano index.nginx-debian.html`のように、root権限で編集を行います。
`index.nginx-debian.html`を以下のように書き換えます。

```sh
<html>
    <body>
        <h1>Server1 - This is from AWS instance1!</h1>
    </body>
</html>
```

`sudo nginx -t`で構文チェックを行い、問題なければ以下のように表示されます。

```sh
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

その後、`sudo systemctl reload nginx`で設定を反映させます。
また、インスタンスを起動した際にNginxも自動で起動するように設定するため、`sudo systemctl enable nginx`を実行します。
先程のように、`sudo systemctl start nginx`でNginxを起動して、ブラウザからアクセスを行うと、設定した画面が表示されます。

![Nginx編集後画面](/images/aws/nginx_edit.png)
*図4:Nginxの編集後画面*

これを同様にして、残り2つのインスタンスにも行います。
:::

### Network Load Balancerの作成
NLBを作成し、用意した3つのインスタンスと結び付けます。

::: details 解答例
実装例です。
実装の詳細は、環境や要件に応じて適宜調整してください。

**ターゲットグループの設定**
ターゲットグループの設定を行い、用意したインスタンス3つを結び付けます。
EC2のターゲットグループの項目における「ターゲットグループの作成ボタン」を押します。

![ターゲットグループ](/images/aws/targetgroup.png)
*図5:ターゲットグループ*

ターゲットグループの作成情報は以下の通りで作成します。

- ターゲットの種類はインスタンス
- ターゲットグループ名は任意
- プロトコルはTCP
- ポート番号は80
- ヘルスチェックプロトコルはTCP

残りはデフォルトのままで設定します。

次へを押し、ターゲットを登録では、用意したインスタンス3つを選択します。
「保留中として以下を含める」を押して次に進みます。
設定を確認し、「ターゲットグループの作成」を押して完了します。

**ロードバランサの作成**
EC2のロードバランサの項目における「ロードバランサの作成」を押し、Network Load Balancerの作成を選ぶ。

![NLB](/images/aws/nlb.png)
*図6:NLB*

ロードバランサの作成情報は以下の通りで作成します。

- ロードバランサ名は任意
- スキームはインターネット向け
- ロードバランサのIPアドレスタイプはIPv4
- VPCはデフォルト
- アベイラビリティーゾーンとサブネットはターゲットグループと同一
- セキュリティグループは用意したインスタンスと同一
- デフォルトアクションは作成したターゲットグループ

残りはデフォルトのままで設定します。
「ロードバランサの作成」を押して、完了します。

**動作確認**
ロードバランサが持つDNS名をブラウザに打ち込むと、用意したインスタンスの表示が確認できます。ブラウザでリロードを行うと表示が変わり、応答するインスタンスが変化することが確認できます。
また、`curl`コマンドで実行しても以下のように変化していることが確認できます。

```sh
$ curl DNS名
<html>
    <body>
        <h1>Server1 - This is from AWS instance1!</h1>
    </body>
</html>
$ curl DNS名
<html>
    <body>
        <h1>Server2 - This is from AWS instance2!</h1>
    </body>
</html>
$ curl DNS名
<html>
    <body>
        <h1>Server2 - This is from AWS instance2!</h1>
    </body>
</html>
```
:::

## まとめ
本記事では、AWSのELBをNetwork Load Balancer(NLB)の実装例とともに解説しました。
ELBには主に3種類のロードバランサのサービスが提供されています。
**Application Load Balancer (ALB)** : OSI参照モデルの第7層であるアプリケーション層で機能します。HTTPやHTTPSのリクエストに対応し、HTTPリクエストの内容をもとにするなど、柔軟な負荷分散を行えます。
**Network Load Balancer (NLB)** : OSI参照モデルの第4層であるトランスポート層で機能します。TCPやUDPのリクエストに対応し、毎秒数百万リクエストといった急激なトラフィック量の増加にも対応することができます。
**Gateway Load Balancer (GWLB)** : OSI参照モデルの第3層であるネットワーク層で機能します。ゲートウェイ機能とトランスポート層の負荷分散機能の両方を備えています。また、すべての通信の検査を行い、安全な通信のみを負荷分散することができます。

AWSのELBを適切に導入することで、目的に応じた負荷分散が可能となり、サービスの安定性を高められます。
