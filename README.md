# <img src="doc/Script%20Launcher_icon.png" width="32"> Script Launcher

複数のルートフォルダを登録し、Python スクリプトをツリー表示で管理・実行できる Blender アドオンです。

<img src="doc/Script%20Launcher_featured.png" width="960">

## 機能

- **複数ルートフォルダ対応** — プリファレンスでスクリプトのルートフォルダを複数登録可能
- **ツリー表示** — サブフォルダを折り畳み可能なツリーで表示。矢印クリックで展開/折り畳み
- **スクリプト実行** — 選択した `.py` ファイルを Blender 上で直接実行
- **テキストエディタで開く** — 選択したスクリプトを Blender 内蔵のテキストエディタに読み込む（既存の Text Editor エリアがあればそこに表示、なければ新規ウィンドウで開く）。外部エディタでファイルが更新されていれば開き直した時点でディスクから読み直します（Blender 側にも未保存の編集がある場合は読み直さず警告）
- **ファイルマネージャーで開く** — 選択したファイル・フォルダを OS のファイルマネージャーで表示
- **展開状態の保持** — リスト更新後もフォルダの展開/折り畳み状態を維持
- **スクリプト検索** — 名前でリアルタイムにフィルタリング。🔍 アイコン横の入力欄に入力、× で解除

## 動作環境

- Blender 4.2 以降

## インストール

1. リリースページから最新の `.zip` ファイルをダウンロード
2. Blender で **Edit → Preferences → Add-ons → Install** を開く
3. ダウンロードした `.zip` を選択して **Install Add-on** をクリック
4. 一覧から **Script Launcher** を有効化

## 使い方

**3D Viewport → Sidebar（N キー）→ Script Launcher** タブから操作します。

| ボタン | 動作 |
|--------|------|
| 🔄 | スクリプト一覧を更新 |
| 📄 | 選択中のスクリプトを Text Editor で開く |
| 📂 | 選択中のアイテムのフォルダをファイルマネージャーで開く |
| ⚙️ | アドオンの Preferences を開く |
| **Run Script** | 選択中の `.py` ファイルを実行 |

サブフォルダ横の **▶ / ▼** をクリックして展開/折り畳みができます。

## 設定

**Edit → Preferences → Add-ons → Script Launcher** から設定できます。

- **Category (N-Panel)** — Sidebar のタブ名を変更（デフォルト: `Script Launcher`）
- **Script Roots** — `+` / `-` ボタンでルートフォルダを追加・削除。リスト下のボックスでパスと表示名を編集

初回インストール時は、アドオンフォルダ内の `scripts/` フォルダが自動的に登録されます。

## 更新履歴

### v1.2.3
- 「テキストエディタで開く」で、外部エディタでの変更がディスクから読み直されるように修正。従来は Blender に読み込み済みの古い内容がそのまま表示され、その状態で保存するとディスク上の新しい内容が失われることがありました
- Blender 側にも未保存の編集がある場合は読み直さず警告します（編集内容を保持。テキストエディタのヘッダーにある Resolve Conflict で解決できます）
- `blender_manifest.toml` にファイルアクセスの permission を宣言

### v1.2.2
- スクリプト実行を Blender 標準オペレーター `bpy.ops.script.python_file_run` に変更（拡張機能プラットフォームのポリシー対応で `exec` を排除）。動作は従来どおり（`__name__ == "__main__"` / `__file__` の設定、`__pycache__` 非生成を維持）

### v1.2.1
- スクリプト実行時に `__pycache__` フォルダが作成されないように変更
- 既存の `__pycache__` フォルダをツリーに表示しないように変更
- スクリプトが `__name__ == "__main__"` として実行されるように変更（`if __name__ == "__main__":` ブロックを含むスクリプトが正しく動作）
- Preferences の表記を整理（`General` セクション、`Category (N-Panel)`）

### v1.2.0
- スクリプト検索機能を追加（リアルタイムフィルタリング）

### v1.1.2
- UIList の非推奨 API (`layout_type`) を削除

### v1.1.1
- ルートフォルダの展開/折り畳みに対応
- Preferences にルートフォルダの上下移動ボタンを追加
- 動作環境を Blender 4.2 以降に更新
- Blender Extension 対応（`blender_manifest.toml` 追加）

### v1.1.0
- 初回リリース

## ライセンス

[GNU General Public License v3.0 or later](https://www.gnu.org/licenses/gpl-3.0.html)
