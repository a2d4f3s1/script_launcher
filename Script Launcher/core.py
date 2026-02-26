import bpy
import bpy.props
import os


# ---------------------------------------------------------------------------
# PropertyGroup: ルートフォルダ項目（プリファレンス用）
# ---------------------------------------------------------------------------

def _on_root_path_update(self, context):
    try:
        build_visible_tree(context)
    except (AttributeError, KeyError):
        pass


class SCRIPTLAUNCHER_FOLDER_ROOT(bpy.types.PropertyGroup):
    path: bpy.props.StringProperty(
        name="Path",
        description="Root folder path for scripts",
        subtype='DIR_PATH',
        default="",
        update=_on_root_path_update,
    )
    label: bpy.props.StringProperty(
        name="Label",
        description="Display name (leave empty to use folder name)",
        default="",
        update=_on_root_path_update,
    )


# ---------------------------------------------------------------------------
# PropertyGroup: ツリーノード（Scene 用フラットリスト）
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_TREE_NODE(bpy.types.PropertyGroup):
    # name は PropertyGroup 標準プロパティを使用
    full_path: bpy.props.StringProperty()
    is_folder: bpy.props.BoolProperty(default=False)
    is_expanded: bpy.props.BoolProperty(default=False)
    indent_level: bpy.props.IntProperty(default=0)
    is_root_header: bpy.props.BoolProperty(default=False)


# ---------------------------------------------------------------------------
# PropertyGroup: Scene に登録するグループ
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_PG(bpy.types.PropertyGroup):
    sl_items: bpy.props.CollectionProperty(type=SCRIPTLAUNCHER_TREE_NODE)
    active_index: bpy.props.IntProperty()


# ---------------------------------------------------------------------------
# ヘルパー: ツリー構築
# ---------------------------------------------------------------------------

def build_visible_tree(context):
    """全ルートフォルダからフラットなツリーリストを再構築する。"""
    addon_prefs = context.preferences.addons[__package__].preferences
    sl_group = context.scene.sl_group

    # 現在の展開状態を保存
    expanded_paths = {
        item.full_path
        for item in sl_group.sl_items
        if item.is_expanded
    }
    known_paths = {item.full_path for item in sl_group.sl_items}

    sl_group.sl_items.clear()

    for i, root in enumerate(addon_prefs.sl_folders):
        if not root.path or not os.path.isdir(root.path):
            continue

        # ルートヘッダー
        display_name = root.label.strip() or os.path.basename(root.path.rstrip('/\\')) or root.path
        header = sl_group.sl_items.add()
        header.name = display_name
        header.full_path = root.path
        header.is_folder = True
        header.is_root_header = True
        header.indent_level = 0
        # 新規ルートはデフォルト展開、既存ルートは保存状態を復元
        header.is_expanded = root.path not in known_paths or root.path in expanded_paths

        # ルート直下のコンテンツ（展開時のみ）
        if header.is_expanded:
            _add_folder_contents(sl_group, root.path, expanded_paths, indent=1)

    # active_index を範囲内に収める
    total = len(sl_group.sl_items)
    if total > 0:
        sl_group.active_index = min(sl_group.active_index, total - 1)


def _add_folder_contents(sl_group, folder_path, expanded_paths, indent):
    """フォルダの中身をツリーリストに追加する（再帰）。"""
    try:
        entries = os.listdir(folder_path)
    except (PermissionError, FileNotFoundError):
        return

    folders = sorted([
        e for e in entries
        if not e.startswith('.') and os.path.isdir(os.path.join(folder_path, e))
    ])
    files = sorted([
        e for e in entries
        if not e.startswith('.') and e.endswith('.py')
        and os.path.isfile(os.path.join(folder_path, e))
    ])

    for name in folders:
        full = os.path.join(folder_path, name)
        item = sl_group.sl_items.add()
        item.name = name
        item.full_path = full
        item.is_folder = True
        item.is_root_header = False
        item.indent_level = indent
        item.is_expanded = full in expanded_paths
        if item.is_expanded:
            _add_folder_contents(sl_group, full, expanded_paths, indent + 1)

    for name in files:
        full = os.path.join(folder_path, name)
        item = sl_group.sl_items.add()
        item.name = name
        item.full_path = full
        item.is_folder = False
        item.is_root_header = False
        item.indent_level = indent


# ---------------------------------------------------------------------------
# UIList: プリファレンス用ルートフォルダ一覧
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_UL_ROOTS(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type not in {'DEFAULT', 'COMPACT'}:
            return
        display = item.label.strip() or os.path.basename(item.path.rstrip('/\\')) or item.path
        layout.label(text=display, icon='FILE_FOLDER')


# ---------------------------------------------------------------------------
# UIList: スクリプトツリー
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_UL_LIST(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type not in {'DEFAULT', 'COMPACT'}:
            return

        # ルートヘッダー行
        if item.is_root_header:
            row = layout.row(align=True)
            expand_icon = 'TRIA_DOWN' if item.is_expanded else 'TRIA_RIGHT'
            op = row.operator("sl.op_togglefolder", text="", icon=expand_icon, emboss=False)
            op.item_index = index
            row.label(text=item.name, icon='FILE_FOLDER')
            return

        # 通常行（フォルダ or ファイル）
        row = layout.row(align=True)

        # インデント（BLANK1 アイコンで空白を表現）
        for _ in range(item.indent_level):
            row.label(text="", icon='BLANK1')

        if item.is_folder:
            expand_icon = 'TRIA_DOWN' if item.is_expanded else 'TRIA_RIGHT'
            op = row.operator("sl.op_togglefolder", text="", icon=expand_icon, emboss=False)
            op.item_index = index
            row.label(text=item.name, icon='FILE_FOLDER')
        else:
            row.label(text="", icon='BLANK1')  # トグルボタン分の空白
            row.label(text=item.name, icon='WORDWRAP_ON')


# ---------------------------------------------------------------------------
# パネルカテゴリ更新（__init__.py から参照）
# ---------------------------------------------------------------------------

def sl_update_category(self, context):
    try:
        bpy.utils.unregister_class(SCRIPTLAUNCHER_PT_PANEL)
    except RuntimeError:
        pass
    if not self.sl_panel_category.strip():
        self.sl_panel_category = "Script Launcher"
    SCRIPTLAUNCHER_PT_PANEL.bl_category = self.sl_panel_category
    bpy.utils.register_class(SCRIPTLAUNCHER_PT_PANEL)


# ---------------------------------------------------------------------------
# パネル
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_PT_PANEL(bpy.types.Panel):
    bl_label = "Script Launcher"
    bl_idname = "SCRIPTLAUNCHER_PT_PANEL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Script Launcher"

    def draw(self, context):
        layout = self.layout
        box = layout.box()

        # ツリーリスト + 縦ボタン列
        sl_group = context.scene.sl_group
        row = box.row()
        row.template_list(
            "SCRIPTLAUNCHER_UL_LIST", "",
            sl_group, "sl_items",
            sl_group, "active_index",
            rows=10,
        )
        col = row.column(align=True)
        col.operator("sl.op_refreshlist", text="", icon='FILE_REFRESH')
        col.operator("sl.op_openfile", text="", icon='CURRENT_FILE')
        col.operator("sl.op_openexplorer", text="", icon='FILEBROWSER')
        col.separator()
        col.operator("sl.op_openpreferences", text="", icon='PREFERENCES')

        # 実行ボタン
        row = box.row()
        row.scale_y = 1.2
        row.operator("sl.op_runscript", text="Run Script", icon='PLAY')
