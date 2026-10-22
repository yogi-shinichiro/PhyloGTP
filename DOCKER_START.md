# Docker配布パッケージ（2026-10-23）

最新の生物種の選択解除、検索結果からの選択、系統樹のPNG・PDF・Newickダウンロードを含みます。
個人用の.env、APIキー、解析結果、モデル本体は同梱していません。

## 自分のPCで起動

ZIPを展開し、このファイルと同じフォルダーでPowerShellを開きます。

```powershell
Copy-Item .env.example .env
notepad .env
```

NCBI_EMAILを自分の連絡先に変更して保存します。.envが既にある場合はコピーで上書きしないでください。

```powershell
docker compose up -d --build app
```

http://localhost:8501 を開きます。初回は環境とAIモデルのダウンロードが必要です。

## Docker Hubにイメージを公開する場合

ZIPを直接アップロードするのではなく、イメージをビルドしてpushします。
YOUR_DOCKERHUB_NAMEは自分のDocker Hubユーザー名に置き換えてください。
公開先のリポジトリと公開範囲を確認してから実行してください。

```powershell
docker build --platform linux/amd64 -t YOUR_DOCKERHUB_NAME/phylogpt:latest .
docker login
docker push YOUR_DOCKERHUB_NAME/phylogpt:latest
```

利用者にはcompose.yamlと.env.exampleも配布してください。
compose.yamlのappのimageをYOUR_DOCKERHUB_NAME/phylogpt:latestに変更し、appのbuild: .を削除すれば、公開イメージを取得して起動できます。
AIはcompose.yamlに定義された別のOllamaコンテナで動きます。アプリのイメージ単独にはAIモデルを含みません。

このパッケージのPython構文とファイル構成を確認しています。今回のパッケージからのDockerビルド・公開はまだ実行していません。
