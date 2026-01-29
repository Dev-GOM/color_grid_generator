import bpy


class COLORGRID_PT_main(bpy.types.Panel):
    """Color Grid Generator Panel"""
    bl_label = "Color Grid Generator"
    bl_idname = "COLORGRID_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Color Grid'

    def draw(self, context):
        layout = self.layout
        props = context.scene.color_grid

        # Image size settings
        box = layout.box()
        box.label(text="Output Size", icon='IMAGE_DATA')
        row = box.row(align=True)
        row.prop(props, "image_width", text="W")
        row.prop(props, "image_height", text="H")

        # Grid size settings
        box = layout.box()
        box.label(text="Grid Size", icon='MESH_GRID')
        row = box.row(align=True)
        row.prop(props, "grid_cols", text="Cols")
        row.prop(props, "grid_rows", text="Rows")

        # Initialize / Load buttons
        row = box.row(align=True)
        row.operator("colorgrid.init_grid", text="Initialize", icon='FILE_REFRESH')
        row.operator("colorgrid.load_grid", text="Load", icon='IMPORT')

        # Check if grid is initialized
        expected_cells = props.grid_cols * props.grid_rows
        grid_valid = len(props.cells) == expected_cells

        if not grid_valid:
            layout.label(text="Initialize or Load to start", icon='INFO')
            return

        # Grid display
        layout.separator()
        box = layout.box()

        # Header with tools
        row = box.row()
        row.label(text=f"Color Grid ({props.grid_cols}x{props.grid_rows})", icon='COLOR')

        sub = row.row(align=True)
        sub.operator("colorgrid.load_grid", text="", icon='IMPORT')
        sub.operator("colorgrid.import_material_colors", text="", icon='MATERIAL')
        sub.operator("colorgrid.fill_grid", text="", icon='SHADING_SOLID')
        sub.operator("colorgrid.randomize_grid", text="", icon='QUESTION')
        sub.operator("colorgrid.clear_grid", text="", icon='X')

        # Draw the color grid
        grid_box = box.column(align=True)

        for row_idx in range(props.grid_rows):
            # Button row (click to open popup)
            btn_row = grid_box.row(align=True)
            btn_row.scale_y = 0.6

            for col in range(props.grid_cols):
                idx = row_idx * props.grid_cols + col
                cell = props.cells[idx]

                op = btn_row.operator(
                    "colorgrid.edit_grid_cell",
                    text="✓" if cell.is_set else "+",
                    emboss=True,
                    depress=cell.is_set
                )
                op.cell_index = idx

            # Color row (display + direct edit)
            color_row = grid_box.row(align=True)
            color_row.scale_y = 0.8

            for col in range(props.grid_cols):
                idx = row_idx * props.grid_cols + col
                cell = props.cells[idx]
                color_row.prop(cell, "color", text="")

        # Output settings
        layout.separator()
        box = layout.box()
        box.label(text="Output", icon='EXPORT')
        row = box.row(align=True)
        row.prop(props, "output_path", text="")
        row.operator("colorgrid.open_folder", text="", icon='FILEBROWSER')

        # Bake button
        row = box.row()
        row.scale_y = 1.5
        row.alert = props.needs_bake  # Red color when needs bake
        row.operator("colorgrid.bake_grid", text="Bake Color Map", icon='RENDER_STILL')

        # Open in editor
        row = box.row(align=True)
        row.operator("colorgrid.open_image", text="Image Editor", icon='IMAGE')
        row.operator("colorgrid.open_uv", text="UV Editor", icon='UV')

        # Create material with color map
        layout.separator()
        box = layout.box()
        box.label(text="Material", icon='MATERIAL')
        row = box.row()
        row.scale_y = 1.3
        row.operator("colorgrid.create_material", text="Create Color Material", icon='NODE_MATERIAL')

        # UV Layout
        layout.separator()
        box = layout.box()
        box.label(text="UV Layout", icon='UV')
        row = box.row()
        row.scale_y = 1.3
        row.operator("colorgrid.auto_uv_layout", text="Auto UV Layout", icon='UV_SYNC_SELECT')

        # Quick Setup (one-click workflow)
        layout.separator()
        box = layout.box()
        box.label(text="Quick Setup", icon='AUTO')
        row = box.row()
        row.scale_y = 1.5
        row.operator("colorgrid.quick_setup", text="Import → Bake → UV Layout", icon='PLAY')


classes = (
    COLORGRID_PT_main,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
