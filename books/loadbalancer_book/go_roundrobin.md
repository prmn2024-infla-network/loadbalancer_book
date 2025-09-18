---
title: "Go言語による負荷分散システムの構築"
---

## 負荷分散
本記事では、ラウンドロビン、最小接続、IPハッシュの3種類の負荷分散手法について紹介します。


### ラウンドロビン方式
最もシンプルで基本的なアルゴリズムです。各リクエストに対して、あらかじめ定められた順番でサーバを切り替えて応答します。
具体的には、サーバ1、サーバ2、サーバ3が存在する場合、各リクエストごとにサーバが1→2→3→1のように順番に変化します。
![ラウンドロビン方式](/images/loadbalance/roundrobin.png)
*図1:ラウンドロビン方式の挙動*

#### メリット・デメリット
メリットは、サーバに均等にアクセスを分散できる点です。また、構造がシンプルかつ明快なので、低コストで簡単に実装することが可能です。
デメリットは、1つのリクエストに時間がかかる場合、待機時間が長くなることです。これは、次々にリクエストが送られ、特定のサーバに負荷が集中してしまうためです。加えて、性能の低いサーバはリクエストを処理しきれず、アクセスが溜まってしまうことから、処理効率が悪くなります。

#### 応用例
このラウンドロビン方式は非常にシンプルなため、様々な応用が可能です。
例えば、「重み付きラウンドロビン方式」があります。これは通常のラウンドロビン方式に加えて、アクセスを分散させるサーバに偏りを持たせるものです。主にサーバごとの性能に差があるときに用いられ、より高性能で応答処理能力が高いサーバには多くのリクエストを送り、処理能力の低いサーバには送るリクエストの量を少なくすることで効率的な負荷分散を行うように設計します。

-----

### 最小接続方式
リクエストを送る際に最も接続数の少ないサーバに送るアルゴリズムです。
具体的には、サーバ1、サーバ2、サーバ3が存在して、サーバ1に接続が2つ、サーバ2に接続が1つ、サーバ3に接続が3つある場合、次に送られてくるリクエストは接続数が最も少ないサーバ2に送られます。
![最小接続方式](/images/loadbalance/leastconnection.png)
*図2:最小接続方式の挙動*

#### メリット・デメリット
メリットは、サーバの負荷が均一になりやすく、実際の処理状況に応じたリクエストの分散が可能なことです。また、一部のサーバに負荷が集中しにくいことから、処理速度や応答性が安定します。
デメリットは、単純に接続数とサーバの負荷がイコールにはならない場合があることです。接続数が少なくても重たい処理を抱えていると、処理時間が長くなります。また、接続数を常に監視する必要があるため、構造が複雑になります。

-----

### IPハッシュ方式
リクエストが来た際に特定の要素を用いてハッシュ値を計算し、それをもとにして応答するサーバを決めるアルゴリズムです。
基本的にはリクエストのヘッダー情報のIPアドレスをもとにしてハッシュ値を計算します。
IPアドレスをもとにした分散を行うと、同一のIPアドレスからのリクエストでは同じサーバが応答します。
他にも、URLやcookieをもとにハッシュ値を計算する手法もあります。
![IPハッシュ方式](/images/loadbalance/ip-hash.png)
*図3:IPハッシュ方式の挙動*


#### メリット・デメリット
メリットは、ログイン情報や状態の管理がしやすく、キャッシュの効率が高くなりやすいことです。これは、同じユーザからのアクセスは基本的に同じIPアドレスとなり、同じサーバに割り当てられるためです。また、接続数や負荷の監視を常にする必要がなく、ハッシュ関数のみで分散ができるため、高速な処理が可能で設定がシンプルです。
デメリットは、計算されたハッシュ値に偏りが出ると、応答するサーバにも偏りが出るため、アクセスが集中してしまう可能性があることです。また、サーバの数が変わると、同じIPアドレスからのリクエストが異なるサーバに割り当てられ、状態の管理が難しくなります。さらに、ハッシュ関数の計算に時間がかかる場合、応答速度が低下する可能性もあります。


## 演習
配布しているファイルを用いて、各負荷分散方式をGo言語で実装できるように構成されています。

仕組みは以下の通りです。
1. Go言語でHttpサーバを立てます。
2. `/`に対してアクセスが行われると、server1,2,3のうちのサーバを1つ選択します。
3. 選んだサーバに対してユーザからのHTTPリクエストのクエリやボディを送信します。
4. 選んだサーバからのレスポンスをユーザに返します。


実装の環境はDocker上で再現します。
構成としては
- docker-compose.yml
- app
    - Dockerfile
    - go.mod
    - main.go

となり、今回記述するところは`main.go`内の`main関数`です。
このファイルの`main関数`内に各負荷分散方式のコードを記述し、実行すると記述した方式の負荷分散が行えます。

実行手順は、ターミナルで`docker-compose up -d`を実行し、コンテナを起動します。
その後、ブラウザから`http://localhost:8080`を検索することで実行できます。
実行結果は、Docker Desktopのログで確認可能です。


### ラウンドロビン方式
基本的な負荷分散方式であるラウンドロビン方式を実装します。

:::details 解答例
以下はラウンドロビン方式を実装した際のコード例です。
実装の詳細は、環境や要件に応じて適宜調整してください。

```go
package main
 
 import (
 	"io"
 	"net/http"
 )
 
 func roundrobin(hostnumber int) int {
 	switch hostnumber {
 	case 0:
 		return 1
 	case 1:
 		return 2
 	case 2:
 		return 0
 	default:
 		return 0
 	}
 }
 
 func main() {
 	var hostnumber int = 0
 	hosts := [3]string{"server1","server2","server3"}
 	//0:server1  ,1:server2  ,2:server3  
 	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
 		resp, err := http.Get("http://"+hosts[hostnumber]+"/")
 		if err != nil {
 			// handle error
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
 			return
 		}
 		defer resp.Body.Close()
 		body, err := io.ReadAll(resp.Body)
 		hostnumber = roundrobin(hostnumber)
 		w.Write(body)
 	})
 
 	http.ListenAndServe(":8080", nil)
 }
```
:::


### IPハッシュ方式
ハッシュ関数を用いた負荷分散方式であるIPハッシュ方式を実装します。

:::details 解答例
以下はIPハッシュ方式を実装した際のコード例です。
実装の詳細は、環境や要件に応じて適宜調整してください。

```go
package main
 
 import (
 	"crypto/md5"
 	"fmt"
 	"io"
 	"net/http"
 	"strconv"
 )
 
 func main() {
 	hosts := [3]string{"server1", "server2", "server3"}
 	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
 		// RemoteAddrの取得
 		remoteAddr := r.RemoteAddr
 
 		// MD5ハッシュの生成
 		hash := md5.Sum([]byte(remoteAddr))
 		hexString := fmt.Sprintf("%x", hash)
 		// ハッシュ値を十進数に変換
 		hostnumber, err := strconv.ParseUint(hexString[:16], 16, 64)
 		if err != nil {
 			// handle error
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
 			return
 		}
 		index := hostnumber % uint64(len(hosts))
 		resp, err := http.Get("http://" + hosts[index] + "/")
 		if err != nil {
 			// handle error
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
 			return
 		}
 		defer resp.Body.Close()
 		body, err := io.ReadAll(resp.Body)
 		if err != nil {
 			// handle error
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
 			return
 		}
 		//numberStr := strconv.FormatUint(hostnumber, 10)
 		numberStr := strconv.FormatUint(index, 10)
 		w.Write([]byte(numberStr))
 		//w.Write([]byte(r.RemoteAddr))
 		//w.Write(body)
 
 	})
 
 	http.ListenAndServe(":8080", nil)
 }
```
 :::

### 最小接続方式
接続数をもとにした負荷分散方式である最小接続方式を実装します。
最小接続方式をgo言語で記述するのは、かなり高度なものとなるため、割愛します。


## まとめ
本記事では、以下の3種類の負荷分散方式について、Go言語での実装例とともに解説しました。

- **ラウンドロビン方式**:シンプルで実装が容易。均等なリクエスト分散が可能。
- **IPハッシュ方式**:動的に負荷を判断して最適なサーバに分散。
- **最小接続方式**:セッション維持やキャッシュ効率に優れるが、偏りに注意が必要。

それぞれの特性を理解し、用途やシステム要件に応じて適切な方式を選択することが重要です。