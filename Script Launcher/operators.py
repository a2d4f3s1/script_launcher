import bpy
import os
import importlib.util

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

        spec = importlib.util.spec_from_file_location(item.name[:-3], item.full_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.report({'INFO'}, f"{item.name} executed successfully")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# ファイルを内部テキストエディタで開く
# ---------------------------------------------------------------------------

def _get_or_load_text(filepath):
    """既存のテキストブロックを再利用、なければ新規読み込み。"""
    norm = os.path.normpath(filepath)
    for text in bpy.data.texts:
        if os.path.normpath(bpy.path.abspath(text.filepath)) == norm:
            return text
    return bpy.data.texts.load(filepath)


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

        text = _get_or_load_text(item.full_path)

        # 既存の Text Editor エリアを探して表示
        for area in context.screen.areas:
            if area.type == 'TEXT_EDITOR':
                area.spaces.active.text = text
                return {'FINISHED'}

        # なければ新規ウィンドウで開く
        bpy.ops.wm.window_new()
        new_win = context.window_manager.windows[-1]
        new_win.screen.areas[0].type = 'TEXT_EDITOR'
        new_win.screen.areas[0].spaces.active.text = text

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
