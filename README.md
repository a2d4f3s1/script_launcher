# <img src="doc/Script%20Launcher_icon.png" width="32"> Script Launcher

複数のルートフォルダを登録し、Python スクリプトをツリー表示で管理・実行できる Blender アドオンです。

<img src="doc/Script%20Launcher_featured.png" width="960">

## 機能

- **複数ルートフォルダ対応** — プリファレンスでスクリプトのルートフォルダを複数登録可能
- **ツリー表示** — サブフォルダを折り畳み可能なツリーで表示。矢印クリックで展開/折り畳み
- **スクリプト実行** — 選択した `.py` ファイルを Blender 上で直接実行
- **テキストエディタで開く** — 選択したスクリプトを Blender 内蔵のテキストエディタに読み込む（既存の Text Editor エリアがあればそこに表示、なければ新規ウィンドウで開く）
- **ファイルマネージャーで開く** — 選択したファイル・フォルダを OS のファイルマネージャーで表示
- **展開状態の保持** — リスト更新後もフォルダの展開/折り畳み状態を維持

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

- **Panel Category** — Sidebar のタブ名を変更（デフォルト: `Script Launcher`）
- **Script Roots** — `+` / `-` ボタンでルートフォルダを追加・削除。リスト下のボックスでパスと表示名を編集

初回インストール時は、アドオンフォルダ内の `scripts/` フォルダが自動的に登録されます。

## 更新履歴

### v1.1.1
- ルートフォルダの展開/折り畳みに対応
- Preferences にルートフォルダの上下移動ボタンを追加
- 動作環境を Blender 4.2 以降に更新
- Blender Extension 対応（`blender_manifest.toml` 追加）

### v1.1.0
- 初回リリース

## ライセンス

[GNU General Public License v3.0 or later](https://www.gnu.org/licenses/gpl-3.0.html)
