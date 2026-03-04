import bpy
import bpy.props
import os


# ---------------------------------------------------------------------------
# ファイルシステムキャッシュ
# ---------------------------------------------------------------------------

_fs_cache: dict = {}


def _get_entries(folder_path):
    """キャッシュからサブフォルダとPYファイル一覧を返す。"""
    if folder_path not in _fs_cache:
        try:
            entries = os.listdir(folder_path)
        except (PermissionError, FileNotFoundError):
            entries = []
        folders = sorted([
            e for e in entries
            if not e.startswith('.') and os.path.isdir(os.path.join(folder_path, e))
        ])
        files = sorted([
            e for e in entries
            if not e.startswith('.') and e.endswith('.py')
            and os.path.isfile(os.path.join(folder_path, e))
        ])
        _fs_cache[folder_path] = (folders, files)
    return _fs_cache[folder_path]


def invalidate_fs_cache():
    """キャッシュを破棄する（Refresh時やパス変更時に呼ぶ）。"""
    _fs_cache.clear()


# ---------------------------------------------------------------------------
# PropertyGroup: ルートフォルダ項目（プリファレンス用）
# ---------------------------------------------------------------------------

def _on_root_path_update(self, context):
    try:
        invalidate_fs_cache()
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

def _on_search_update(self, context):
    try:
        # ツリー再構築前に現在の選択パスを保存
        current_path = ""
        if self.sl_items and 0 <= self.active_index < len(self.sl_items):
            current_path = self.sl_items[self.active_index].full_path
        build_visible_tree(context)
        # 再構築後にfull_pathで選択を復元
        if current_path:
            for i, item in enumerate(self.sl_items):
                if item.full_path == current_path:
                    self.active_index = i
                    break
        if context.area:
            context.area.tag_redraw()
    except (AttributeError, KeyError):
        pass


class SCRIPTLAUNCHER_PG(bpy.types.PropertyGroup):
    sl_items: bpy.props.CollectionProperty(type=SCRIPTLAUNCHER_TREE_NODE)
    active_index: bpy.props.IntProperty()
    search_text: bpy.props.StringProperty(
        name="Search",
        default="",
        options={"TEXTEDIT_UPDATE"},
        update=_on_search_update,
    )


# ---------------------------------------------------------------------------
# ヘルパー: ツリー構築
# ---------------------------------------------------------------------------

def build_visible_tree(context):
    """全ルートフォルダからフラットなツリーリストを再構築する。"""
    addon_prefs = context.preferences.addons[__package__].preferences
    sl_group = context.scene.sl_group
    query = sl_group.search_text.strip().lower()

    # 現在の展開状態を保存（通常モード用）
    expanded_paths = {
        item.full_path
        for item in sl_group.sl_items
        if item.is_expanded
    }
    known_paths = {item.full_path for item in sl_group.sl_items}

    sl_group.sl_items.clear()

    for root in addon_prefs.sl_folders:
        if not root.path or not os.path.isdir(root.path):
            continue

        display_name = root.label.strip() or os.path.basename(root.path.rstrip('/\\')) or root.path

        if query:
            # 検索モード: ルートを仮追加し、子孫にマッチがなければ取り消す
            idx = len(sl_group.sl_items)
            header = sl_group.sl_items.add()
            header.name = display_name
            header.full_path = root.path
            header.is_folder = True
            header.is_root_header = True
            header.indent_level = 0
            header.is_expanded = True
            children_added = _add_folder_contents(sl_group, root.path, expanded_paths, indent=1, query=query)
            if not children_added and query not in display_name.lower():
                sl_group.sl_items.remove(idx)
        else:
            # 通常モード
            is_new = root.path not in known_paths
            header = sl_group.sl_items.add()
            header.name = display_name
            header.full_path = root.path
            header.is_folder = True
            header.is_root_header = True
            header.indent_level = 0
            header.is_expanded = is_new or root.path in expanded_paths
            if header.is_expanded:
                _add_folder_contents(sl_group, root.path, expanded_paths, indent=1)

    # active_index を範囲内に収める
    total = len(sl_group.sl_items)
    if total > 0:
        sl_group.active_index = min(sl_group.active_index, total - 1)


def _add_folder_contents(sl_group, folder_path, expanded_paths, indent, query=""):
    """フォルダの中身をツリーリストに追加する（再帰）。

    queryが指定された場合は検索モードで動作し、仮追加→不要なら取り消す方式で
    二重スキャンなしにマッチ判定と追加を同時に行う。マッチがあればTrueを返す。
    """
    folders, files = _get_entries(folder_path)
    any_added = False

    for name in folders:
        full = os.path.join(folder_path, name)
        if query:
            if query in name.lower():
                # フォルダ名マッチ: 表示のみ、中身は展開しない
                item = sl_group.sl_items.add()
                item.name = name
                item.full_path = full
                item.is_folder = True
                item.is_root_header = False
                item.indent_level = indent
                item.is_expanded = False
                any_added = True
            else:
                # 仮追加して再帰。子孫にマッチがなければ取り消す
                idx = len(sl_group.sl_items)
                item = sl_group.sl_items.add()
                item.name = name
                item.full_path = full
                item.is_folder = True
                item.is_root_header = False
                item.indent_level = indent
                item.is_expanded = True
                if _add_folder_contents(sl_group, full, expanded_paths, indent + 1, query):
                    any_added = True
                else:
                    sl_group.sl_items.remove(idx)
        else:
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
        if query and query not in name.lower():
            continue
        item = sl_group.sl_items.add()
        item.name = name
        item.full_path = full
        item.is_folder = False
        item.is_root_header = False
        item.indent_level = indent
        any_added = True

    return any_added


# ---------------------------------------------------------------------------
# UIList: プリファレンス用ルートフォルダ一覧
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_UL_ROOTS(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        display = item.label.strip() or os.path.basename(item.path.rstrip('/\\')) or item.path
        layout.label(text=display, icon='FILE_FOLDER')


# ---------------------------------------------------------------------------
# UIList: スクリプトツリー
# ---------------------------------------------------------------------------

class SCRIPTLAUNCHER_UL_LIST(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
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

        sl_group = context.scene.sl_group

        # 検索バー
        row = box.row(align=True)
        row.prop(sl_group, "search_text", text="", icon='VIEWZOOM')
        if sl_group.search_text:
            row.operator("sl.op_clear_search", text="", icon='X')

        # ツリーリスト + 縦ボタン列
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
