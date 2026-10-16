# google-drive-uploader

ローカル（自分のMac）にあるファイルを、Google Drive API を使って Google ドライブにアップロードする Python プログラムです。

- アップロード先は、マイドライブの `API連携テスト` フォルダです。フォルダが無ければ、プログラムが自動で作ります
- 同じ名前のファイルがある場合は、上書きするかどうかを確認します
- 自分の Google アカウントでログインする OAuth 方式を使っています

## ファイル構成

```
google-drive-uploader/
├── main.py            # プログラム本体
├── sample.txt         # 動作確認用のファイル
├── README.md          # このファイル
├── 要件定義書.md       # 要件定義書
└── .gitignore         # GitHub に載せないファイルの一覧
```

次の2つのファイルは、秘密の情報なのでリポジトリには含めていません。

| ファイル | 内容 | 用意の仕方 |
|---|---|---|
| `credentials.json` | OAuth クライアントの鍵 | 下の「事前準備」の手順で各自作成して置く |
| `token.json` | ログインしたときにできる許可証 | 初回ログインで自動で作られる |

## 必要な環境

- Python 3
- Google アカウント（個人の Gmail で使えます）
- Google Cloud のプロジェクト

## 事前準備（Google Cloud Console で行う）

1. [Google Cloud Console](https://console.cloud.google.com/) で、使うプロジェクトを選ぶ
2. **Google Drive API** を有効にする
   - 「API とサービス」→「ライブラリ」で `Google Drive API` を検索して「有効にする」
3. **OAuth 同意画面**を設定する
   - 対象：**外部**
   - テストユーザー：自分の Gmail アドレスを追加する
4. **OAuth クライアントID** を作成する
   - 「API とサービス」→「認証情報」→「認証情報を作成」→「OAuth クライアントID」
   - アプリケーションの種類：**デスクトップアプリ**
5. 作成したクライアントの JSON をダウンロードし、名前を `credentials.json` に変えて、`main.py` と同じフォルダに置く

> Google ドライブに `API連携テスト` フォルダを手で作る必要はありません。プログラムが作ります。
> 権限の範囲を `drive.file`（このプログラムが作ったファイルとフォルダだけを扱える）にしているため、手で作ったフォルダはプログラムから見えません。

## インストール方法

1. このリポジトリをダウンロードする

   ```bash
   git clone https://github.com/m-tsuna/google-drive-uploader.git
   cd google-drive-uploader
   ```

2. 必要なライブラリをインストールする

   ```bash
   pip install google-api-python-client google-auth google-auth-oauthlib
   ```

3. 「事前準備」で用意した `credentials.json` を、`main.py` と同じフォルダに置く

## 使い方

1. ターミナルで実行する

   ```bash
   python main.py
   ```

2. 初回だけ、ブラウザで Google のログイン画面が開きます。ログインして「許可」を押してください
   - 「このアプリは Google で確認されていません」と表示された場合は、「続行」を押して進めます（自分で作ったテスト中のアプリのため）
   - 許可すると `token.json` が作られ、次回からはログインしなくても使えます

3. アップロードするファイルのパスを入力して Enter を押します
   - Finder からファイルをターミナルにドラッグ＆ドロップすると、パスを入力できます
   - `~/Desktop/sample.txt` のように、`~`（ホームフォルダ）で始まるパスも使えます
   - パスが空欄・存在しない・フォルダだった場合は、理由が表示されて、もう一度聞かれます

4. アップロードが終わると、ファイル名と、ドライブで開ける URL が表示されます

### 実行例

初めてアップロードするとき：

```
アップロードするファイルのパスを入力してください: /Users/xxxx/Desktop/sample.txt
ドライブに「API連携テスト」フォルダを作成しました。
アップロードしました: sample.txt
URL: https://drive.google.com/file/d/xxxxxxxx/view
```

同じ名前のファイルをもう一度アップロードするとき：

```
アップロードするファイルのパスを入力してください: /Users/xxxx/Desktop/sample.txt
「API連携テスト」に同じ名前のファイル（sample.txt）があります。上書きしますか？（y/n）: y
上書きしました: sample.txt
URL: https://drive.google.com/file/d/xxxxxxxx/view
```

- `y`：既存のファイルを上書きします。古い中身は、ドライブの「版の履歴」に残ります
- `n`：同じ名前の別のファイルとして追加します

## 注意

- OAuth 同意画面が「テスト中」の場合、ログインの有効期限は7日ほどです。期限が切れると、次に実行したときに自動でログイン画面が開きます
- ファイルはそのままの形式でアップロードします（Google ドキュメントなどの形式には変換しません）
- アップロード元のファイル（自分のパソコンにあるファイル）は書き換えません
- `credentials.json` と `token.json` は、自分のドライブに入るための鍵と許可証です。他の人に渡したり、GitHub に載せたりしないでください（`.gitignore` で除外しています）
