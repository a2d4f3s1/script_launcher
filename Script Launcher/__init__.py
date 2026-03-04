bl_info = {
    "name": "Script Launcher",
    "author": "Moteki",
    "version": (1, 1, 2),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Script Launcher",
    "description": "Manage and run Python scripts from multiple root folders",
    "category": "Other",
}

if "bpy" in locals():
    import importlib
    if "core" in locals():
        importlib.reload(core)
    if "operators" in locals():
        importlib.reload(operators)

import bpy
import bpy.props
from bpy.app.handlers import persistent
from . import core
from . import operators


class SCRIPTLAUNCHER_PREFERENCES(bpy.types.AddonPreferences):
    bl_idname = __package__

    sl_panel_category: bpy.props.StringProperty(
        name="Panel Category",
        default="Script Launcher",
        description="Category tab name for Script Launcher's panel",
        update=core.sl_update_category,
    )

    sl_folders: bpy.props.CollectionProperty(
        type=core.SCRIPTLAUNCHER_FOLDER_ROOT,
        name="Script Roots",
    )

    active_root_index: bpy.props.IntProperty(
        name="Active Root Index",
        default=0,
    )

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "sl_panel_category")

        layout.separator()
        layout.label(text="Script Roots:")

        row = layout.row()
        row.template_list(
            "SCRIPTLAUNCHER_UL_ROOTS", "",
            self, "sl_folders",
            self, "active_root_index",
            rows=4,
        )
        col = row.column(align=True)
        col.operator("sl.op_add_root", text="", icon='ADD')
        col.operator("sl.op_remove_root", text="", icon='REMOVE')
        col.separator()
        col.operator("sl.op_move_root", text="", icon='TRIA_UP').direction = 'UP'
        col.operator("sl.op_move_root", text="", icon='TRIA_DOWN').direction = 'DOWN'

        if self.sl_folders and self.active_root_index < len(self.sl_folders):
            folder = self.sl_folders[self.active_root_index]
            box = layout.box()
            box.prop(folder, "path", text="Path")
            box.prop(folder, "label", text="Label")


classes = [
    core.SCRIPTLAUNCHER_FOLDER_ROOT,
    core.SCRIPTLAUNCHER_TREE_NODE,
    SCRIPTLAUNCHER_PREFERENCES,
    core.SCRIPTLAUNCHER_PG,
    core.SCRIPTLAUNCHER_UL_ROOTS,
    core.SCRIPTLAUNCHER_UL_LIST,
    core.SCRIPTLAUNCHER_PT_PANEL,
    operators.SCRIPTLAUNCHER_OT_REFRESHLIST,
    operators.SCRIPTLAUNCHER_OT_RUNSCRIPT,
    operators.SCRIPTLAUNCHER_OT_OPENFILE,
    operators.SCRIPTLAUNCHER_OT_OPENEXPLORER,
    operators.SCRIPTLAUNCHER_OT_OPENPREFERENCES,
    operators.SCRIPTLAUNCHER_OT_TOGGLEFOLDER,
    operators.SCRIPTLAUNCHER_OT_ADD_ROOT,
    operators.SCRIPTLAUNCHER_OT_REMOVE_ROOT,
    operators.SCRIPTLAUNCHER_OT_MOVE_ROOT,
]


@persistent
def load_handler(dummy):
    try:
        bpy.ops.sl.op_refreshlist()
    except Exception as e:
        print(f"Script Launcher: failed to refresh list on load: {e}")


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    prefs = bpy.context.preferences.addons[__package__].preferences

    core.sl_update_category(prefs, bpy.context)

    # 初回インストール時にデフォルトの scripts フォルダを自動登録
    if not prefs.sl_folders:
        import os
        item = prefs.sl_folders.add()
        item.path = os.path.join(os.path.dirname(__file__), "scripts")
        item.label = "Default Scripts"

    bpy.types.Scene.sl_group = bpy.props.PointerProperty(type=core.SCRIPTLAUNCHER_PG)
    bpy.app.handlers.load_post.append(load_handler)


def unregister():
    bpy.app.handlers.load_post.remove(load_handler)

    del bpy.types.Scene.sl_group

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)


if __name__ == "__main__":
    register()
