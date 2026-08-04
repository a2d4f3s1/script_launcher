import bpy
import functools
import os
import sys

from . import core


# ---------------------------------------------------------------------------
# リスト更新
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_OT_REFRESHLIST(bpy.types.Operator):
    bl_idname = "sl.op_refreshlist"
    bl_label = "Refresh List"
    bl_description = "Reload scripts list from all root folders"

    def execute(self, context):
        core.invalidate_fs_cache()
        core.build_visible_tree(context)
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# スクリプト実行
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_OT_RUNSCRIPT(bpy.types.Operator):
    bl_idname = "sl.op_runscript"
    bl_label = "Run Script"
    bl_description = "Execute the selected script"

    def execute(self, context):
        sl_group = context.scene.sl_group

        if not sl_group.sl_items:
            self.report({'WARNING'}, "No scripts in list")
            return {'CANCELLED'}

        item = sl_group.sl_items[sl_group.active_index]

        if item.is_root_header:
            self.report({'WARNING'}, "Select a script file to run")
            return {'CANCELLED'}

        if item.is_folder:
            self.report({'WARNING'}, "Select a script file, not a folder")
            return {'CANCELLED'}

        if not os.path.isfile(item.full_path):
            self.report({'ERROR'}, f"File not found: {item.full_path}")
            return {'CANCELLED'}

        # 実行は Blender 標準オペレーター script.python_file_run に委譲する。
        # これは内部で __name__ == "__main__" / __file__ を設定してファイルを実行し
        # （Text Editor の Run Script と同じセマンティクス）、アドオン側のコードから
        # exec/eval を排除する（extensions.blender.org のポリシー対応）。
        #
        # スクリプトが import するモジュールの __pycache__ でユーザーの
        # スクリプトフォルダを汚さないよう、実行中だけ bytecode 書き込みを抑止
        old_flag = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            result = bpy.ops.script.python_file_run(filepath=item.full_path)
        except RuntimeError as exc:
            # スクリプト内の例外は bpy.ops 経由で RuntimeError として伝播する
            self.report({'ERROR'}, f"{item.name} failed: {exc}")
            return {'CANCELLED'}
        finally:
            sys.dont_write_bytecode = old_flag

        if 'CANCELLED' in result:
            self.report({'ERROR'}, f"{item.name} failed (see system console)")
            return {'CANCELLED'}

        self.report({'INFO'}, f"{item.name} executed successfully")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# ファイルを内部テキストエディタで開く
# ---------------------------------------------------------------------------

def _find_loaded_text(filepath):
    """同じファイルを指す既存のテキストブロックを返す。無ければ None。

    texts.load() は同じパスでも重複したブロックを作るため、必ず先に探す。
    """
    norm = os.path.normpath(filepath)
    for text in bpy.data.texts:
        if text.is_in_memory or not text.filepath:
            continue
        if os.path.normpath(bpy.path.abspath(text.filepath)) == norm:
            return text
    return None


def _sync_action(text):
    """外部変更に対する処置を返す: 'NONE' / 'RELOAD' / 'CONFLICT'。

    is_modified はディスクとメモリの差、is_dirty は未保存編集の有無。両方立って
    いる場合は自動で読み直すと編集が失われるので、ユーザーに解決してもらう。

    Blender の検知は mtime の秒単位比較なので、読み込みと同じ秒に外部保存された
    場合だけ取りこぼす。その場合も次に開いたときに拾える。
    """
    if not text.is_modified:
        return 'NONE'
    return 'CONFLICT' if text.is_dirty else 'RELOAD'


def _show_in_text_editor(context, text):
    """text をテキストエディタに表示し、(window, area) を返す。"""
    for area in context.screen.areas:
        if area.type == 'TEXT_EDITOR':
            area.spaces.active.text = text
            return context.window, area

    # なければ新規ウィンドウで開く
    bpy.ops.wm.window_new()
    new_win = context.window_manager.windows[-1]
    area = new_win.screen.areas[0]
    area.type = 'TEXT_EDITOR'
    area.spaces.active.text = text
    return new_win, area


def _reload_text(context, window, area, text):
    """ディスクから読み直す。安全に実行できなければ何もせず False を返す。

    text.reload の実処理は SpaceText と ARegion を NULL チェックなしで参照する
    一方、poll は edit_text しか見ない。つまり poll が通ることは安全の根拠に
    ならず、region に触れるかどうかはスクロール位置などで変わるため「前回は
    落ちなかった」も根拠にならない。条件が揃わない呼び出しは実行しない。

    edit_text / space_data は渡さず area から解決させる。手渡しすると
    「space が無いまま poll だけ通る」状態を自分で作ってしまう。
    """
    if text.is_dirty:
        return False
    if area is None or area.type != 'TEXT_EDITOR':
        return False

    space = area.spaces.active
    if not isinstance(space, bpy.types.SpaceTextEditor) or space.text is not text:
        return False

    region = next((r for r in area.regions if r.type == 'WINDOW'), None)
    if region is None or region.width <= 0 or region.height <= 0:
        return False

    with context.temp_override(window=window, area=area, region=region):
        if not bpy.ops.text.reload.poll():
            return False
        return 'FINISHED' in bpy.ops.text.reload()


def _retry_reload(filepath):
    """一度きりの再試行。タイマーから呼ばれる。

    新規ウィンドウを作った直後はエリアがまだ読み直せる状態とは限らないため、
    次のタイミングでもう一度だけ試す。ウィンドウやエリアの参照は持ち越さず、
    その場で引き直す（閉じられていれば空振りするだけで済む）。
    """
    text = _find_loaded_text(filepath)
    if text is None or _sync_action(text) != 'RELOAD':
        return None

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'TEXT_EDITOR' and area.spaces.active.text is text:
                _reload_text(bpy.context, window, area, text)
                return None
    return None


class SCRIPTLAUNCHER_OT_OPENFILE(bpy.types.Operator):
    bl_idname = "sl.op_openfile"
    bl_label = "Open in Text Editor"
    bl_description = "Open the selected .py file in Blender's Text Editor"

    def execute(self, context):
        sl_group = context.scene.sl_group

        if not sl_group.sl_items:
            self.report({'WARNING'}, "No scripts in list")
            return {'CANCELLED'}

        item = sl_group.sl_items[sl_group.active_index]

        if item.is_folder or item.is_root_header:
            self.report({'WARNING'}, "Select a script file to open")
            return {'CANCELLED'}

        if not os.path.isfile(item.full_path):
            self.report({'ERROR'}, f"File not found: {item.full_path}")
            return {'CANCELLED'}

        text = _find_loaded_text(item.full_path)
        action = _sync_action(text) if text is not None else 'NONE'
        if text is None:
            text = bpy.data.texts.load(item.full_path)

        window, area = _show_in_text_editor(context, text)

        if action == 'RELOAD':
            if _reload_text(context, window, area, text):
                self.report({'INFO'}, f"{item.name} reloaded from disk")
            else:
                # 黙って古い内容を表示すると、そのまま保存されてディスク側の
                # 新しい内容が失われる。必ず知らせたうえで一度だけ再試行する。
                self.report({'WARNING'},
                            f"{item.name} is older than the file on disk - "
                            "reopen it or use Reload from Disk before saving")
                bpy.app.timers.register(
                    functools.partial(_retry_reload, item.full_path),
                    first_interval=0.0)
        elif action == 'CONFLICT':
            self.report({'WARNING'},
                        "Edited both in Blender and on disk - use Resolve "
                        "Conflict in the Text Editor header")

        return {'FINISHED'}


# ---------------------------------------------------------------------------
# 選択中アイテムのフォルダをエクスプローラーで開く
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_OT_OPENEXPLORER(bpy.types.Operator):
    bl_idname = "sl.op_openexplorer"
    bl_label = "Open in Explorer"
    bl_description = "Open the selected item's folder in the system file manager"

    def execute(self, context):
        sl_group = context.scene.sl_group

        if not sl_group.sl_items:
            self.report({'WARNING'}, "No items in list")
            return {'CANCELLED'}

        item = sl_group.sl_items[sl_group.active_index]

        # ファイルなら親フォルダ、フォルダ/ルートヘッダーはそのパス
        if item.is_folder or item.is_root_header:
            target = item.full_path
        else:
            target = os.path.dirname(item.full_path)

        if not target or not os.path.exists(target):
            self.report({'ERROR'}, f"Path not found: {target}")
            return {'CANCELLED'}

        bpy.ops.wm.path_open(filepath=target)
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# プリファレンスを開く
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_OT_OPENPREFERENCES(bpy.types.Operator):
    bl_idname = "sl.op_openpreferences"
    bl_label = "Open Preferences"
    bl_description = "Open Script Launcher addon preferences"

    def execute(self, context):
        bpy.ops.preferences.addon_show(module=__package__)
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# フォルダのトグル展開
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_OT_TOGGLEFOLDER(bpy.types.Operator):
    bl_idname = "sl.op_togglefolder"
    bl_label = "Toggle Folder"
    bl_description = "Expand or collapse this folder"

    item_index: bpy.props.IntProperty()

    def execute(self, context):
        sl_group = context.scene.sl_group

        if self.item_index < 0 or self.item_index >= len(sl_group.sl_items):
            return {'CANCELLED'}

        item = sl_group.sl_items[self.item_index]
        if not item.is_folder:
            return {'CANCELLED'}

        # 展開状態を反転してからツリーを再構築
        item.is_expanded = not item.is_expanded
        current_path = item.full_path

        core.build_visible_tree(context)

        # 操作したフォルダにフォーカスを戻す
        for i, node in enumerate(sl_group.sl_items):
            if node.full_path == current_path:
                sl_group.active_index = i
                break

        return {'FINISHED'}


# ---------------------------------------------------------------------------
# 検索クリア
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_OT_CLEAR_SEARCH(bpy.types.Operator):
    bl_idname = "sl.op_clear_search"
    bl_label = "Clear Search"
    bl_description = "Clear the search filter"

    def execute(self, context):
        context.scene.sl_group.search_text = ""
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# ルートフォルダの追加・削除（プリファレンス用）
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_OT_ADD_ROOT(bpy.types.Operator):
    bl_idname = "sl.op_add_root"
    bl_label = "Add Root Folder"
    bl_description = "Add a new root folder to the script roots list"

    def execute(self, context):
        addon_prefs = context.preferences.addons[__package__].preferences
        addon_prefs.sl_folders.add()
        addon_prefs.active_root_index = len(addon_prefs.sl_folders) - 1
        return {'FINISHED'}


class SCRIPTLAUNCHER_OT_REMOVE_ROOT(bpy.types.Operator):
    bl_idname = "sl.op_remove_root"
    bl_label = "Remove Root Folder"
    bl_description = "Remove the selected root folder from the list"

    def execute(self, context):
        addon_prefs = context.preferences.addons[__package__].preferences

        if not addon_prefs.sl_folders:
            return {'CANCELLED'}

        idx = addon_prefs.active_root_index
        addon_prefs.sl_folders.remove(idx)
        addon_prefs.active_root_index = max(0, min(idx, len(addon_prefs.sl_folders) - 1))

        core.invalidate_fs_cache()
        core.build_visible_tree(context)
        return {'FINISHED'}


class SCRIPTLAUNCHER_OT_MOVE_ROOT(bpy.types.Operator):
    bl_idname = "sl.op_move_root"
    bl_label = "Move Root Folder"
    bl_description = "Move the selected root folder up or down"

    direction: bpy.props.EnumProperty(
        items=[('UP', 'Up', ''), ('DOWN', 'Down', '')],
    )

    def execute(self, context):
        addon_prefs = context.preferences.addons[__package__].preferences
        idx = addon_prefs.active_root_index
        count = len(addon_prefs.sl_folders)

        if self.direction == 'UP' and idx > 0:
            addon_prefs.sl_folders.move(idx, idx - 1)
            addon_prefs.active_root_index -= 1
        elif self.direction == 'DOWN' and idx < count - 1:
            addon_prefs.sl_folders.move(idx, idx + 1)
            addon_prefs.active_root_index += 1
        else:
            return {'CANCELLED'}

        core.build_visible_tree(context)
        return {'FINISHED'}
