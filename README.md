# PhyloGPT

日本語の特徴・機能から遺伝子候補を探し、比較したい生物種を選び、指定遺伝子のCDS配列から系統樹を作成するStreamlitアプリです。この公開版は指定遺伝子からの解析に対応します。

## 機能

- Ollama上のgemma3:4bによる遺伝子候補と日本語説明
- NCBI Gene・Ortholog・Taxonomyからの情報取得
- 分類群、日本語名・学名による生物種の検索と選択
- CDS配列の取得、MAFFTでの整列、RAxML-NGでの系統樹推定と表示

## Dockerで起動

Docker Desktopを起動してください。WindowsではLinuxコンテナとWSL 2バックエンドを使用します。Docker Composeが必要です。アプリのイメージはlinux/amd64向けで、AIを含めてCPUで動作します。

GitHubからコードを取得し、compose.yamlと同じフォルダでPowerShellを開きます。

```powershell
Copy-Item .env.example .env
```

Linuxでは`cp .env.example .env`を使用します。すでに.envがある場合は上書きせず、その設定を確認してください。

`.env`の`NCBI_EMAIL`を自分の連絡先メールアドレスに変更します。`NCBI_API_KEY`は任意です。既定のAIモデルは`OLLAMA_MODEL=gemma3:4b`です。メールアドレスやキーを含む.envはGitHubに載せません。

```text
docker compose up --build -d
```

初回は解析環境のビルドと、Ollamaのイメージ・モデルの取得に時間と保存容量が必要です。保存済みのモデルは再利用し、未取得の場合だけダウンロードします。モデルの準備が完了してからアプリが起動します。ホストPCへのPython、解析ツール、Ollamaの個別インストールは不要です。

起動後は **http://localhost:8501** を開きます。8501を使用中の場合は.envに`PHYLOGPT_PORT=8502`を設定して起動し、http://localhost:8502 を開いてください。

CPUでの初回AI読み込みには時間がかかる場合があります。AIへの待ち時間は`.env`の`OLLAMA_TIMEOUT_SECONDS`で変更でき、既定は600秒です。Docker版は同時実行モデル・リクエストを1つに制限し、読み込んだモデルを30分保持します。

## 操作

1. 調べたい特徴やタンパク質を日本語で入力し、遺伝子候補を確認します。
2. 遺伝子情報を確認して解析する遺伝子を選びます。
3. オルソログ候補の一覧から4種以上を選択します。
4. CDS取得を実行し、取得結果を確認します。
5. 系統樹作成を実行して結果を確認します。

## 状態確認と停止

```text
docker compose ps -a
docker compose logs -f model-init
docker compose logs -f app
```

ログ表示はCtrl+Cで終了します。アプリとAIを停止するには次を実行してください。実行中の解析も停止します。

```text
docker compose down
```

通常のdownでは、解析データ用ボリューム`phylogpt_analysis-data`とモデル用ボリューム`phylogpt_ollama-models`は残ります。`down -v`は保存データも削除するため、保持したい場合は実行しないでください。中断した解析は自動再開されません。

結果をPCに取り出す場合は、コピー先resultsフォルダを作成し、アプリ起動中に次を実行します。

```text
docker compose cp app:/home/mambauser/data/. ./results/
```

## 解析ツールの確認

```text
docker compose exec app python -c "from tool_runner import check_tools; print(check_tools())"
```

アプリにはNCBI Datasets CLI、MAFFT、RAxML-NGを同梱します。AIは別コンテナのOllamaに接続します。バージョンの確認状況はVALIDATION.mdを参照してください。

## ファイル構成

| ファイル | 役割 |
| --- | --- |
| app.py | アプリ画面 |
| ai_gene.py / gene_info.py | 遺伝子候補の提示、情報取得と説明 |
| ortholog.py / taxonomy.py | オルソログ取得と分類 |
| get_CDS_v3.py / phylogeny_CDS.py | CDS取得と系統樹推定 |
| tool_runner.py | Linux/WSL上の解析ツールの実行 |
| settings.py | 環境変数と.envの読込 |
| container_start.py | Docker内の起動処理 |
| Dockerfile / environment.yml / requirements.txt | 実行環境の構築 |
| compose.yaml / .env.example | コンテナ構成と設定例 |

## 操作画面と出力例

この公開用コピーにはまだ画面・出力画像を同梱していません。docsフォルダなどに追加し、使用遺伝子、生物種、解析条件と結果の説明を付けてください。

## 制約

インターネット接続が必要です。取得可能な配列はNCBIの登録状況に依存します。AIの提案・説明は原典と照合してください。アラインメント、解析条件、枝の支持値を確認して結果を解釈してください。複数利用者の同時解析には対応しておらず、同じ遺伝子の出力は上書きされます。

## Dockerなしで起動する場合

Python 3.10以降とrequirements.txtのライブラリ、Linux/WSL内のNCBI Datasets CLI・MAFFT・RAxML-NG、Ollamaを準備します。`.env`のPHYLOGPT_TOOL_PATHをLinux側のツールのbinディレクトリに設定し、OLLAMA_URLで接続先を指定します。

```text
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## 参考資料

- https://docs.docker.com/compose/how-tos/startup-order/
- https://docs.ollama.com/docker
- https://docs.streamlit.io/deploy/tutorials/docker
