"""
Googleドライブ アップロードプログラム（課題1：Google ドライブ API）

ローカル（自分のMac）にあるファイルを、Google ドライブの
「API連携テスト」フォルダにアップロードする。

使い方：ターミナルで  python main.py  を実行する。
"""

import mimetypes
import os
import re
import sys
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# ============================================================
# 設定（ここをまとめて書いておく）
# ============================================================

# このプログラム（main.py）が置いてあるフォルダ
BASE_DIR = Path(__file__).resolve().parent

# OAuth クライアントの鍵（Google Cloud Console からダウンロードしたもの）
CREDENTIALS_FILE = BASE_DIR / "credentials.json"

# 初回ログインで自動で作られる許可証
TOKEN_FILE = BASE_DIR / "token.json"

# プログラムに許可する範囲。drive.file は「このプログラムが作ったファイルとフォルダだけ」を扱える
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# アップロード先のフォルダ名（マイドライブの直下に作る）
FOLDER_NAME = "API連携テスト"

# Google ドライブで「フォルダ」を表す種類（MIMEタイプ）
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

# 拡張子から種類が分からないときに使う「種類不明のファイル」
DEFAULT_MIME_TYPE = "application/octet-stream"


# ============================================================
# F1 ログイン（認証）
# ============================================================
def login():
    """
    Google にログインして、ドライブを操作するための「サービス」を返す。

    1. token.json があれば、それを読み込む
    2. 期限切れで更新できるなら、自動で更新する
    3. token.json が無い・更新できない場合は、ブラウザでログイン画面を開く
    4. 許可されたら、次回のために token.json を保存する
    """
    creds = None

    # token.json があれば読み込む（壊れていたら無視して、ログインからやり直す）
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except ValueError:
            creds = None

    # 期限切れだが更新できる場合は、自動で更新する
    if creds and not creds.valid and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            # 同意画面が「テスト中」だと約7日で更新できなくなる → ログインし直す
            print("ログインの有効期限が切れていたため、もう一度ログインします。")
            creds = None

    # まだ使える許可証が無い場合は、ブラウザでログインする
    if not creds or not creds.valid:
        # credentials.json が無いとログインできないので、理由を表示して終了する（F7）
        if not CREDENTIALS_FILE.exists():
            show_error_and_exit(
                f"{CREDENTIALS_FILE.name} が見つかりません。\n"
                f"Google Cloud Console で OAuth クライアントID（デスクトップアプリ）を作成し、\n"
                f"ダウンロードした JSON を「{CREDENTIALS_FILE.name}」という名前で\n"
                f"次のフォルダに置いてください: {BASE_DIR}"
            )

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
        except ValueError:
            show_error_and_exit(
                f"{CREDENTIALS_FILE.name} の中身が正しくありません。\n"
                "OAuth クライアントID（デスクトップアプリ）の JSON をダウンロードし直してください。"
            )

        # ブラウザが開き、ログインして「許可」を押すと続きに進む
        creds = flow.run_local_server(port=0)

        # 次回からログインしなくていいように、許可証を保存する
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    # ドライブを操作するための「サービス」を作って返す
    return build("drive", "v3", credentials=creds)


# ============================================================
# F2 ファイルの指定
# ============================================================
def clean_path_text(text):
    """
    入力されたパスの文字列を整える。

    - 前後の空白を取り除く
    - ドラッグ＆ドロップで付く前後の ' や " を取り除く
    - ドラッグ＆ドロップで付く \\（例：「my\\ file.txt」の \\）を取り除く
    - ~（ホームフォルダ）を実際の場所に置き換える
    """
    text = text.strip()

    # 前後が同じ引用符（' または "）で囲まれていたら外す
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        text = text[1:-1]
    else:
        # 引用符で囲まれていない場合、「\ 」や「\(」のように
        # 文字の前に付いた \ を取り除く（Mac のドラッグ＆ドロップ対策）
        text = re.sub(r"\\(.)", r"\1", text)

    # ~ で始まるパスを、ホームフォルダのパスに変える
    return os.path.expanduser(text)


def ask_file_path():
    """
    アップロードするファイルのパスを聞いて、Path として返す。
    空欄・存在しない・フォルダ のときは、理由を表示してもう一度聞く。
    """
    while True:
        text = input("アップロードするファイルのパスを入力してください: ")
        path_text = clean_path_text(text)

        # 何も入力されなかった
        if path_text == "":
            print("パスが入力されていません。もう一度入力してください。")
            continue

        path = Path(path_text)

        # ファイルが存在しない
        if not path.exists():
            print(f"ファイルが見つかりません: {path}")
            print("パスが正しいか確認して、もう一度入力してください。")
            continue

        # フォルダが指定された（ファイルではない）
        if path.is_dir():
            print(f"フォルダが指定されました: {path}")
            print("フォルダではなく、ファイルのパスを入力してください。")
            continue

        return path


# ============================================================
# F3 アップロード先フォルダの用意
# ============================================================
def escape_query_text(text):
    """
    ドライブの検索条件（クエリ）に名前を入れるとき、
    \\ と ' が特別な意味を持たないように前に \\ を付ける。
    （例：「It's.txt」のような名前でも正しく検索できるようにする）
    """
    return text.replace("\\", "\\\\").replace("'", "\\'")


def prepare_folder(service):
    """
    マイドライブに「API連携テスト」フォルダがあればその ID を返し、
    なければ新しく作ってその ID を返す。

    - ゴミ箱に入っているフォルダは使わない（trashed = false）
    - 同じ名前のフォルダが2つ以上あれば、最初に見つかったものを使う
    - drive.file スコープなので、このプログラムが作ったフォルダだけが見える
    """
    query = (
        f"name = '{escape_query_text(FOLDER_NAME)}'"
        f" and mimeType = '{FOLDER_MIME_TYPE}'"
        " and 'root' in parents"
        " and trashed = false"
    )
    result = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
    ).execute()
    folders = result.get("files", [])

    # 見つかったら、最初のものを使う
    if folders:
        return folders[0]["id"]

    # 見つからなければ、マイドライブの直下に作る
    metadata = {
        "name": FOLDER_NAME,
        "mimeType": FOLDER_MIME_TYPE,
        "parents": ["root"],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    print(f"ドライブに「{FOLDER_NAME}」フォルダを作成しました。")
    return folder["id"]


# ============================================================
# F4 同じ名前のファイルの確認
# ============================================================
def find_same_name_file(service, folder_id, file_name):
    """
    「API連携テスト」の中に同じ名前のファイルがあるか調べる。

    - あれば、いちばん新しく更新されたファイルの ID を返す
    - なければ None を返す
    - ゴミ箱に入っているファイルは数えない
    """
    query = (
        f"name = '{escape_query_text(file_name)}'"
        f" and '{folder_id}' in parents"
        " and trashed = false"
    )
    result = service.files().list(
        q=query,
        spaces="drive",
        orderBy="modifiedTime desc",  # 新しく更新された順に並べる
        fields="files(id, name, modifiedTime)",
    ).execute()
    files = result.get("files", [])

    if files:
        return files[0]["id"]
    return None


def ask_overwrite(file_name):
    """
    「上書きしますか？（y/n）」と聞く。
    y なら True、n なら False を返す。それ以外が入力されたら、もう一度聞く。
    """
    while True:
        answer = input(
            f"「{FOLDER_NAME}」に同じ名前のファイル（{file_name}）があります。"
            "上書きしますか？（y/n）: "
        ).strip().lower()

        if answer == "y":
            return True
        if answer == "n":
            return False
        print("y か n で入力してください。")


# ============================================================
# F5 アップロード
# ============================================================
def upload_file(service, file_path, folder_id, overwrite_file_id=None):
    """
    ファイルをドライブにアップロードして、アップロードしたファイルの情報を返す。

    - overwrite_file_id が None なら、フォルダに新しく追加する
    - overwrite_file_id があれば、そのファイルの中身を上書きする
      （古い中身はドライブの「版の履歴」に残る）
    - Google ドキュメントなどの形式には変換せず、そのままの形式で送る
    - 大きいファイルでも途中から再開できる「再開可能アップロード」で送る
    - ローカルの元ファイルは読むだけで、書き換えない
    """
    # 拡張子からファイルの種類（MIMEタイプ）を判断する。分からなければ「種類不明」にする
    mime_type, _ = mimetypes.guess_type(file_path.name)
    if mime_type is None:
        mime_type = DEFAULT_MIME_TYPE

    # 送る中身を用意する（resumable=True で再開可能アップロードになる）
    media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)

    if overwrite_file_id:
        # 既存のファイルの中身を上書きする
        request = service.files().update(
            fileId=overwrite_file_id,
            media_body=media,
            fields="id, name",
        )
    else:
        # フォルダに新しいファイルとして追加する
        metadata = {
            "name": file_path.name,
            "parents": [folder_id],
        }
        request = service.files().create(
            body=metadata,
            media_body=media,
            fields="id, name",
        )

    # 少しずつ送る。最後まで送り終わると response にファイルの情報が入る
    response = None
    while response is None:
        _status, response = request.next_chunk()

    return response


# ============================================================
# F6 結果の表示
# ============================================================
def show_result(uploaded_file, overwritten):
    """
    アップロードしたファイル名と、ドライブで開ける URL を表示する。
    上書きした場合は「上書きしました」、新規なら「アップロードしました」と出す。
    """
    url = f"https://drive.google.com/file/d/{uploaded_file['id']}/view"

    if overwritten:
        print(f"上書きしました: {uploaded_file['name']}")
    else:
        print(f"アップロードしました: {uploaded_file['name']}")
    print(f"URL: {url}")


# ============================================================
# F7 エラー表示
# ============================================================
def show_error_and_exit(message):
    """
    原因が分かる日本語のエラーメッセージを表示して、プログラムを終了する。
    """
    print(f"エラー: {message}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# メインの処理（上の関数を順番に呼ぶ）
# ============================================================
def main():
    """
    プログラム全体の流れ：
    ログイン → ファイルの指定 → フォルダの用意 → 同じ名前の確認 → アップロード → 結果の表示
    """
    try:
        # F1 ログイン
        service = login()

        # F2 ファイルの指定
        file_path = ask_file_path()

        # F3 アップロード先フォルダの用意
        folder_id = prepare_folder(service)

        # F4 同じ名前のファイルの確認
        same_file_id = find_same_name_file(service, folder_id, file_path.name)
        overwrite_file_id = None
        if same_file_id and ask_overwrite(file_path.name):
            overwrite_file_id = same_file_id

        # F5 アップロード
        uploaded_file = upload_file(service, file_path, folder_id, overwrite_file_id)

        # F6 結果の表示
        show_result(uploaded_file, overwritten=overwrite_file_id is not None)

    except HttpError as error:
        # Google ドライブとのやりとりで失敗した（F7）
        show_error_and_exit(
            "Google ドライブとのやりとりに失敗しました。\n"
            f"ステータスコード: {error.status_code}\n"
            f"詳細: {error.reason}"
        )
    except PermissionError as error:
        # ローカルのファイルを読む権限が無かった（F7）
        show_error_and_exit(f"ファイルを読み込めませんでした（権限がありません）: {error.filename}")
    except OSError as error:
        # ネットワークにつながらない、ファイルが読めない など（F7）
        show_error_and_exit(
            "アップロードに失敗しました。インターネット接続やファイルを確認してください。\n"
            f"詳細: {error}"
        )
    except (KeyboardInterrupt, EOFError):
        # Ctrl + C などで途中でやめた場合
        print("\n中断しました。")
        sys.exit(1)


# このファイルを直接実行したときだけ main() を動かす
if __name__ == "__main__":
    main()
