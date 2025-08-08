---
title: "Go言語による負荷分散システムの作成"
---

## 負荷分散
今回取り上げる負荷分散の方式は、ラウンドロビン、最小接続、ip-hashの三種類の負荷分散を行っていきます。
以下、各方式の解説から始まり、演習で実装してもらう流れとなります。

### ラウンドロビン方式
この方式は最もシンプルで基本的なアルゴリズムとなっています。動作内容は応答するサーバを順番に変化させていくものです。
具体的には、サーバ1、サーバ2、サーバ3が存在する場合、サーバにアクセスをするごとにサーバが1-->2-->3-->1といったように順番に変化していきます。
![ラウンドロビン方式](/images/loadbalance/roundrobin.png)

#### メリット・デメリット
メリットは、サーバに対してそれぞれ均等にアクセスを分散させることができることです。また、構造がシンプル明快なゆえに、低コストで簡単に実装することが可能となります。
デメリットは、1つのリクエストに時間がかかってしまう場合、待機時間が長くなってしまうことです。これは、次々にリクエストが送られてきてしまうために特定のサーバに負荷が集中しやすくなるためです。加えて、性能の低いサーバはリクエストを処理しきれず、アクセスが溜まりやすくなることから、効率が悪くなってしまいます。

#### 応用例
このラウンドロビン方式は非常にシンプルなため、様々な応用が可能です。
例えば、重みづけラウンドロビン方式というものがあります。これは通常のラウンドロビン方式に加えて、アクセスを分散させるサーバに偏りを持たせるものです。主にサーバごとの性能に差があるときに用いられ、より高性能で応答処理能力が高いサーバには多くのリクエストを送り、処理能力の低いサーバには送るリクエストの量を少なくすることで効率的な負荷分散を行うように設計します。

### 最小接続方式
この方式はリクエストを送る際に最も接続数の少ないサーバに送るアルゴリズムとなっています。
具体的には、サーバ1、サーバ2、サーバ3が存在して、サーバ1にコネクションが2つ、サーバ2にコネクションが1つ、サーバ3にコネクションが3つあるとすると、次に送られてくるリクエストは接続数であるコネクションが最も少ないサーバ2に送られます。
![最小接続方式](/images/loadbalance/leastconnection.png)

#### メリット・デメリット
メリットは、サーバの負荷が均一になりやすく、実際の処理状況に応じたリクエストの分散が可能となることです。また、一部のサーバに負荷が集中しにくいことから、処理速度や応答性が安定しやすくなります。
デメリットは、単純に接続数とサーバの負荷がイコールにはならない場合があり、接続数が少なくても、重たい処理を抱えていると処理に時間がかかってしまうことです。また、接続数を常に監視する必要があるため、構造が複雑になりやすいものとなることです。

### ip-hash方式
この方式はリクエストが来た際に特定の要素を用いてハッシュ値を計算し、それをもとにして応答するサーバを決めるものとなります。
基本的にはリクエストのヘッダー情報のIPアドレスをもとにしてハッシュ値を計算します。
IPアドレスをもとにした分散を行うと、同じIPアドレスからのリクエストでは同じサーバが応答するようになります。
他の要素では、URLをもとにしたハッシュやcookieをもとにしたハッシュ計算するものもあります。
![ip-hash方式](/images/loadbalance/ip-hash.png)

#### メリット・デメリット
メリットは、ログイン情報や状態の管理がしやすく、キャッシュの効率が高くなりやすいことです。これは、同じユーザからのアクセスは基本的に同じIPアドレスとなり、同じサーバに割り当てられるためです。また、接続数や負荷の監視を常にする必要がなく、ハッシュ関数のみで分散ができるため、高速な処理が可能で設定がシンプルとなります。
デメリットは、計算されたハッシュ値に偏りが出ると、応答するサーバにも偏りが出るため、アクセスが集中してしまう可能性があることです。また、サーバの数が変わったりすると、同じIPアドレスからのリクエストが異なるサーバに割り当てられることになり、状態の管理が難しくなることです。さらに、ハッシュ関数の計算に時間がかかる場合、応答速度が低下する可能性もあります。


## 演習
以降から実践編ということで負荷分散方式をGo言語で記述していきます。
配布しているファイルを使用し、一部を記述してもらう形になります。

仕組みとしては
1. Go言語でHttpサーバを立てます。
2. `/`に対してアクセスが行われると、server1,2,3のうちのサーバを1つ選択します。
3. 選んだサーバに対してユーザからのHTTPリクエストのクエリやボディを送信します。
4. 選んだサーバからのレスポンスをユーザに返します。

となります。

実装の環境はDocker上で再現していきます。
構成としては
- docker-compose.yml
- app
    - Dockerfile
    - go.mod
    - main.go

となり、今回記述してもらうところは`main.go`の`func main()`になります。
このファイルの`main`関数内に各負荷分散方式のコードを記述してもらい、実行すると記述した方式の負荷分散が行えます。

実行手順は、ターミナル上で`docker-compose up -d`というコマンドを打ち込み、コンテナを立ち上げます。
その後、ブラウザから`http://localhost:8080`を検索することで実行できます。
実行結果は、Docker Desktop上のログから確認できます。


### ラウンドロビン方式
まずは、基本的な負荷分散方式であるラウンドロビン方式を作成しましょう。
ラウンドロビンの記述では`main.go`のファイルの中の`func main(){}`の中を記述します。

:::details 解答例
`func main(){}`の中は以下のようなコードが回答例となります。

```go
package main
 
 import (
 	"io"
 	"net/http"
 )
 
 func roundrobin(hostnumber int)int{
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


### ip-hash方式
次にip-hash方式を作成していきましょう。
ip-hash方式でも`main.go`のファイルの中の`func main(){}`に記述します。
:::details 回答例
`func main(){}`の中は以下のようなコードが回答例となります。
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
 		}
 		index := hostnumber % uint64(len(hosts))
 		resp, err := http.Get("http://" + hosts[index] + "/")
 		if err != nil {
 			// handle error
 		}
 		defer resp.Body.Close()
 		body, err := io.ReadAll(resp.Body)
 		if err != nil {
 			// handle error
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
最後に最小接続方式を作成していきましょう。
最小接続方式でも`main.go`のファイルの中の`func main(){}`に記述します。

:::details 回答例
`func main(){}`の中は以下のようなコードが回答例となります。

```go
package main
 
 import (
 	"context"
 	"encoding/json"
 	"io"
 	"log"
 	"net"
 	"net/http"
 	"sync"
 	"sync/atomic"
 )
 
 type contextKey string
 
 const connKey contextKey = "conn"
 
 var (
 	// 各バックエンドサーバの接続カウンター
 	counts [3]uint64
 	// net.Conn とバックエンドのインデックス（0～2）を対応付けるマップ
 	connBackend sync.Map // key: net.Conn, value: int
 )
 
 func main() {
 	hosts := [3]string{"server1", "server2", "server3"}
 	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
 		// 最小接続法: 各サーバの現在のアクティブ接続数を調べ、最小のサーバを選択する
 		//最小の接続をさがす
 		index := 0
 		minCon := atomic.LoadUint64(&counts[0])
 		for i := 1; i < len(hosts); i++ {
 			conns := atomic.LoadUint64(&counts[i])
 			if conns < minCon {
 				minCon = conns
 				index = i
 			}
 		}
 
 		// リクエストのコンテキストから、コネクションを取得する
 		if connValue := r.Context().Value(connKey); connValue != nil {
 			if conn, ok := connValue.(net.Conn); ok {
 				// このリクエストに対して選択されたバックエンドのインデックスを記録
 				connBackend.Store(conn, index)
 			}
 		}
 
 		resp, err := http.Get("http://" + hosts[index] + "/")
 		if err != nil {
 			// handle error
 		}
 		defer resp.Body.Close()
 		body, err := io.ReadAll(resp.Body)
 		if err != nil {
 			// handle error
 		}
 		w.Write(body)
 
 	})
 	// /metrics エンドポイントでカウンタ確認
 	http.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
 		metrics := map[string]uint64{
 			"server1": atomic.LoadUint64(&counts[0]),
 			"server2": atomic.LoadUint64(&counts[1]),
 			"server3": atomic.LoadUint64(&counts[2]),
 		}
 		w.Header().Set("Content-Type", "application/json")
 		jsonData, err := json.Marshal(metrics)
 		if err != nil {
 			http.Error(w, "Error generating metrics", http.StatusInternalServerError)
 			return
 		}
 		w.Write(jsonData)
 	})
 
 	// カスタム HTTP サーバを作成。ConnContext で connection をリクエストコンテキストに注入。
 	server := &http.Server{
 		Addr: ":8080",
 		// ConnContext を使い、各接続の情報をコンテキストに埋め込む
 		ConnContext: func(ctx context.Context, c net.Conn) context.Context {
 			return context.WithValue(ctx, connKey, c)
 		},
 		// ConnState で接続状態が変わったとき、その接続がどのバックエンドに対応しているかを
 		// connBackend のマップから取り出し、対応する counts を原子的に更新する
 		ConnState: func(conn net.Conn, state http.ConnState) {
 			if idxValue, ok := connBackend.Load(conn); ok {
 				idx := idxValue.(int)
 				switch state {
 				// リクエスト開始のタイミングでカウントを増やす
 				case http.StateActive:
 					atomic.AddUint64(&counts[idx], 1)
 				// Idle 状態は、意図に応じた処理にする
 				case http.StateIdle:
 					// 必要に応じた処理を追加
 					//atomic.AddUint64(&counts[idx], 1)
 				// 接続が閉じられた・ハイジャックされたときは、最後に念のためマップから削除
 				case http.StateClosed, http.StateHijacked:
 					atomic.AddUint64(&counts[idx], ^uint64(0))
 					connBackend.Delete(conn)
 				}
 			}
 		},
 	}
 
 	// カスタムサーバを起動（これにより ConnState の効果も有効になります）
 	log.Fatal(server.ListenAndServe())
 }
```
:::