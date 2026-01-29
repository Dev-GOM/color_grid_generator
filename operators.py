import bpy
import os
import json
import random
from bpy.props import IntProperty, FloatVectorProperty, BoolProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from .properties import set_skip_color_update


class COLORGRID_OT_init_grid(bpy.types.Operator):
    """Initialize the color grid with default values"""
    bl_idname = "colorgrid.init_grid"
    bl_label = "Initialize Grid"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.color_grid

        # Push undo
        try:
            bpy.ops.ed.undo_push(message="Before Initialize Grid")
        except Exception:
            pass

        set_skip_color_update(True)
        try:
            # Clear and recreate cells
            props.cells.clear()
            target_count = props.grid_cols * props.grid_rows

            for i in range(target_count):
                cell = props.cells.add()
                cell.color = (0.0, 0.0, 0.0, 1.0)
                cell.is_set = False

            self.report({'INFO'}, f"Initialized {props.grid_cols}x{props.grid_rows} grid")
            return {'FINISHED'}
        finally:
            set_skip_color_update(False)


def save_color_grid_json(context):
    """Save color grid metadata to JSON file"""
    props = context.scene.color_grid

    output_path = bpy.path.abspath(props.output_path)
    if not output_path:
        return

    json_path = os.path.splitext(output_path)[0] + '.json'

    output_dir = os.path.dirname(json_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    cell_colors = []
    for idx, cell in enumerate(props.cells):
        row = idx // props.grid_cols
        col = idx % props.grid_cols
        cell_colors.append({
            'row': row,
            'col': col,
            'r': cell.color[0],
            'g': cell.color[1],
            'b': cell.color[2],
            'a': cell.color[3],
            'is_set': cell.is_set
        })

    metadata = {
        'image_width': props.image_width,
        'image_height': props.image_height,
        'grid_cols': props.grid_cols,
        'grid_rows': props.grid_rows,
        'cells': cell_colors
    }

    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    except Exception:
        pass


class COLORGRID_OT_set_cell_color(bpy.types.Operator):
    """Set cell color and close popup"""
    bl_idname = "colorgrid.set_cell_color"
    bl_label = "Set Color"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    cell_index: IntProperty()
    cell_color: FloatVectorProperty(size=4)

    def execute(self, context):
        bpy.ops.ed.undo_push(message="Before Set Cell Color")

        props = context.scene.color_grid

        if self.cell_index >= len(props.cells):
            return {'CANCELLED'}

        cell = props.cells[self.cell_index]

        set_skip_color_update(True)
        try:
            cell.color = tuple(self.cell_color)
            cell.is_set = True
            props.needs_bake = True
        finally:
            set_skip_color_update(False)

        save_color_grid_json(context)

        self.report({'INFO'}, "Cell color set")
        return {'FINISHED'}

    def invoke(self, context, event):
        result = self.execute(context)
        if result == {'FINISHED'}:
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return result

    def modal(self, context, event):
        return {'FINISHED'}


class COLORGRID_OT_clear_cell(bpy.types.Operator):
    """Clear cell to black and close popup"""
    bl_idname = "colorgrid.clear_cell"
    bl_label = "Clear"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    cell_index: IntProperty()

    def execute(self, context):
        bpy.ops.ed.undo_push(message="Before Clear Cell")

        props = context.scene.color_grid

        if self.cell_index >= len(props.cells):
            return {'CANCELLED'}

        cell = props.cells[self.cell_index]

        set_skip_color_update(True)
        try:
            cell.color = (0.0, 0.0, 0.0, 1.0)
            cell.is_set = False
            props.needs_bake = True
        finally:
            set_skip_color_update(False)

        save_color_grid_json(context)

        self.report({'INFO'}, "Cell cleared")
        return {'FINISHED'}

    def invoke(self, context, event):
        result = self.execute(context)
        if result == {'FINISHED'}:
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return result

    def modal(self, context, event):
        return {'FINISHED'}


class COLORGRID_OT_edit_grid_cell(bpy.types.Operator):
    """Edit a single grid cell"""
    bl_idname = "colorgrid.edit_grid_cell"
    bl_label = "Edit Cell"
    bl_description = "Edit or clear this cell"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    cell_index: IntProperty(
        name="Cell Index",
        default=0
    )

    cell_color: FloatVectorProperty(
        name="Color",
        subtype='COLOR_GAMMA',
        size=4,
        default=(0.5, 0.5, 0.5, 1.0),
        min=0.0,
        max=1.0
    )

    def invoke(self, context, event):
        props = context.scene.color_grid

        if self.cell_index < len(props.cells):
            cell = props.cells[self.cell_index]
            self.cell_color = cell.color[:]

        return context.window_manager.invoke_popup(self, width=280)

    def draw(self, context):
        layout = self.layout
        props = context.scene.color_grid

        # Show cell position
        row_idx = self.cell_index // props.grid_cols
        col_idx = self.cell_index % props.grid_cols
        layout.label(text=f"Cell [{row_idx}, {col_idx}]", icon='MESH_GRID')

        layout.separator()

        # Color picker
        layout.template_color_picker(self, "cell_color", value_slider=True)
        layout.prop(self, "cell_color", text="")

        layout.separator()

        # Color info (RGB values)
        box = layout.box()
        row = box.row()
        row.label(text=f"R: {self.cell_color[0]:.3f}")
        row.label(text=f"G: {self.cell_color[1]:.3f}")
        row.label(text=f"B: {self.cell_color[2]:.3f}")

        # Hex color
        r = int(self.cell_color[0] * 255)
        g = int(self.cell_color[1] * 255)
        b = int(self.cell_color[2] * 255)
        box.label(text=f"Hex: #{r:02X}{g:02X}{b:02X}")

        layout.separator()

        # Action buttons
        row = layout.row(align=True)
        row.scale_y = 1.3
        op_set = row.operator("colorgrid.set_cell_color", text="Set Color", icon='CHECKMARK')
        op_set.cell_index = self.cell_index
        op_set.cell_color = self.cell_color

        op_clear = row.operator("colorgrid.clear_cell", text="Clear", icon='X')
        op_clear.cell_index = self.cell_index

    def execute(self, context):
        return {'FINISHED'}


class COLORGRID_OT_fill_grid(bpy.types.Operator):
    """Fill all cells with a single color"""
    bl_idname = "colorgrid.fill_grid"
    bl_label = "Fill Grid"
    bl_options = {'REGISTER', 'UNDO'}

    color: FloatVectorProperty(
        name="Fill Color",
        subtype='COLOR_GAMMA',
        size=4,
        default=(0.5, 0.5, 0.5, 1.0),
        min=0.0,
        max=1.0
    )

    overwrite_set: BoolProperty(
        name="Overwrite Set Cells",
        description="Also overwrite cells that have been explicitly set",
        default=False
    )

    def execute(self, context):
        props = context.scene.color_grid

        set_skip_color_update(True)
        try:
            count = 0
            for cell in props.cells:
                if self.overwrite_set or not cell.is_set:
                    cell.color = self.color
                    cell.is_set = True
                    count += 1

            if count > 0:
                props.needs_bake = True

            save_color_grid_json(context)
            self.report({'INFO'}, f"Filled {count} cells")
            return {'FINISHED'}
        finally:
            set_skip_color_update(False)

    def invoke(self, context, event):
        # Push undo before opening dialog
        try:
            bpy.ops.ed.undo_push(message="Before Fill Grid")
        except Exception:
            pass

        # Count set cells for warning
        props = context.scene.color_grid
        set_count = sum(1 for cell in props.cells if cell.is_set)

        if set_count > 0:
            self._set_count = set_count
        else:
            self._set_count = 0

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "color")

        if hasattr(self, '_set_count') and self._set_count > 0:
            box = layout.box()
            box.label(text=f"Warning: {self._set_count} cells already set", icon='ERROR')
            box.prop(self, "overwrite_set")


class COLORGRID_OT_randomize_grid(bpy.types.Operator):
    """Fill grid with random colors"""
    bl_idname = "colorgrid.randomize_grid"
    bl_label = "Randomize Grid"
    bl_options = {'REGISTER', 'UNDO'}

    overwrite_set: BoolProperty(
        name="Overwrite Set Cells",
        description="Also overwrite cells that have been explicitly set",
        default=False
    )

    def execute(self, context):
        props = context.scene.color_grid

        set_skip_color_update(True)
        try:
            count = 0
            for cell in props.cells:
                if self.overwrite_set or not cell.is_set:
                    cell.color = (
                        random.random(),
                        random.random(),
                        random.random(),
                        1.0
                    )
                    cell.is_set = True
                    count += 1

            if count > 0:
                props.needs_bake = True

            save_color_grid_json(context)
            self.report({'INFO'}, f"Randomized {count} cells")
            return {'FINISHED'}
        finally:
            set_skip_color_update(False)

    def invoke(self, context, event):
        # Push undo before opening dialog
        try:
            bpy.ops.ed.undo_push(message="Before Randomize Grid")
        except Exception:
            pass

        # Count set cells for warning
        props = context.scene.color_grid
        set_count = sum(1 for cell in props.cells if cell.is_set)

        if set_count > 0:
            self._set_count = set_count
            return context.window_manager.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout

        if hasattr(self, '_set_count') and self._set_count > 0:
            box = layout.box()
            box.label(text=f"Warning: {self._set_count} cells already set", icon='ERROR')
            box.prop(self, "overwrite_set")


class COLORGRID_OT_clear_grid(bpy.types.Operator):
    """Clear all cells in the grid"""
    bl_idname = "colorgrid.clear_grid"
    bl_label = "Clear Grid"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.color_grid

        set_skip_color_update(True)
        try:
            for cell in props.cells:
                cell.color = (0.0, 0.0, 0.0, 1.0)
                cell.is_set = False

            props.needs_bake = True

            save_color_grid_json(context)
            self.report({'INFO'}, "Grid cleared")
            return {'FINISHED'}
        finally:
            set_skip_color_update(False)

    def invoke(self, context, event):
        # Push undo before executing
        try:
            bpy.ops.ed.undo_push(message="Before Clear Grid")
        except Exception:
            pass

        # Count set cells for warning
        props = context.scene.color_grid
        set_count = sum(1 for cell in props.cells if cell.is_set)

        if set_count > 0:
            return context.window_manager.invoke_confirm(self, event)
        else:
            return self.execute(context)


class COLORGRID_OT_bake_grid(bpy.types.Operator):
    """Bake the color grid to an image file"""
    bl_idname = "colorgrid.bake_grid"
    bl_label = "Bake Color Map"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.color_grid

        # Validate
        if len(props.cells) != props.grid_cols * props.grid_rows:
            self.report({'ERROR'}, "Grid not initialized")
            return {'CANCELLED'}

        output_path = bpy.path.abspath(props.output_path)
        if not output_path:
            self.report({'ERROR'}, "Output path not set")
            return {'CANCELLED'}

        # Ensure directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Create backup if file already exists (only one backup)
        if os.path.exists(output_path):
            base, ext = os.path.splitext(output_path)
            backup_path = f"{base}_backup{ext}"
            try:
                import shutil
                shutil.copy2(output_path, backup_path)
            except Exception as e:
                self.report({'WARNING'}, f"Could not create backup: {e}")

        # Create image
        img_name = os.path.basename(output_path)
        img = bpy.data.images.new(
            name=img_name,
            width=props.image_width,
            height=props.image_height,
            alpha=True
        )

        # Calculate cell dimensions
        cell_width = props.image_width // props.grid_cols
        cell_height = props.image_height // props.grid_rows

        # Create pixel data
        pixels = [0.0] * (props.image_width * props.image_height * 4)

        for row in range(props.grid_rows):
            for col in range(props.grid_cols):
                cell_idx = row * props.grid_cols + col
                cell = props.cells[cell_idx]

                # Calculate pixel range for this cell
                x_start = col * cell_width
                x_end = (col + 1) * cell_width if col < props.grid_cols - 1 else props.image_width

                # Flip Y axis (Blender images are bottom-up)
                y_start = (props.grid_rows - 1 - row) * cell_height
                y_end = (props.grid_rows - row) * cell_height if row > 0 else props.image_height

                # Fill pixels
                for y in range(y_start, y_end):
                    for x in range(x_start, x_end):
                        pixel_idx = (y * props.image_width + x) * 4
                        pixels[pixel_idx] = cell.color[0]
                        pixels[pixel_idx + 1] = cell.color[1]
                        pixels[pixel_idx + 2] = cell.color[2]
                        pixels[pixel_idx + 3] = cell.color[3]

        # Apply pixels
        img.pixels = pixels
        img.filepath_raw = output_path
        img.file_format = 'PNG'
        img.save()

        # Save JSON metadata
        self._save_json(context, output_path)

        # Mark as baked (no longer needs bake)
        props.needs_bake = False

        # Refresh existing images in editors
        existing_img = bpy.data.images.get(img_name)
        if existing_img and existing_img != img:
            existing_img.reload()

        # Refresh all IMAGE_EDITOR areas
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.tag_redraw()

        # Remove temporary image
        bpy.data.images.remove(img)

        self.report({'INFO'}, f"Color map saved to: {output_path}")
        return {'FINISHED'}

    def _save_json(self, context, output_path):
        """Save color grid metadata to JSON file"""
        props = context.scene.color_grid
        json_path = os.path.splitext(output_path)[0] + '.json'

        cell_colors = []
        for idx, cell in enumerate(props.cells):
            row = idx // props.grid_cols
            col = idx % props.grid_cols
            cell_colors.append({
                'row': row,
                'col': col,
                'r': cell.color[0],
                'g': cell.color[1],
                'b': cell.color[2],
                'a': cell.color[3],
                'is_set': cell.is_set
            })

        metadata = {
            'image_width': props.image_width,
            'image_height': props.image_height,
            'grid_cols': props.grid_cols,
            'grid_rows': props.grid_rows,
            'cells': cell_colors
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)


class COLORGRID_OT_import_material_colors(bpy.types.Operator):
    """Import base colors from selected object's materials"""
    bl_idname = "colorgrid.import_material_colors"
    bl_label = "Import Material Colors"
    bl_description = "Import base colors from selected object's materials to empty grid cells"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        props = context.scene.color_grid
        obj = context.active_object

        # Check if grid is initialized
        expected_cells = props.grid_cols * props.grid_rows
        if len(props.cells) != expected_cells:
            self.report({'ERROR'}, "Grid not initialized")
            return {'CANCELLED'}

        # Collect base colors from materials
        material_colors = []
        for mat in obj.data.materials:
            if mat is None:
                continue

            color = self._get_base_color(mat)
            if color:
                material_colors.append((mat.name, color))

        if not material_colors:
            self.report({'WARNING'}, "No materials with base color found")
            return {'CANCELLED'}

        # Helper to compare colors (with tolerance)
        def colors_equal(c1, c2, tolerance=0.01):
            return (abs(c1[0] - c2[0]) < tolerance and
                    abs(c1[1] - c2[1]) < tolerance and
                    abs(c1[2] - c2[2]) < tolerance)

        # Find existing colors in grid (cells that are set)
        existing_colors = []
        for idx, cell in enumerate(props.cells):
            if cell.is_set:
                existing_colors.append((idx, cell.color[:3]))

        # Push undo state before making changes
        bpy.ops.ed.undo_push(message="Before Import Material Colors")

        # Track results
        added_count = 0
        duplicate_infos = []

        # Use property access with skip flag for undo support
        set_skip_color_update(True)
        try:
            for mat_name, color in material_colors:
                # Check if color already exists in grid
                duplicate_idx = None
                for idx, existing in existing_colors:
                    if colors_equal(color, existing):
                        duplicate_idx = idx
                        break

                if duplicate_idx is not None:
                    # Calculate grid position (row, col)
                    row = duplicate_idx // props.grid_cols
                    col = duplicate_idx % props.grid_cols
                    duplicate_infos.append(f"{mat_name} -> Grid [{row},{col}]")
                    continue

                # Find next empty cell (not set)
                empty_idx = None
                for idx, cell in enumerate(props.cells):
                    if not cell.is_set:
                        empty_idx = idx
                        break

                if empty_idx is None:
                    self.report({'WARNING'}, f"No empty cells left for {mat_name}")
                    break

                # Assign color to cell
                props.cells[empty_idx].color = (color[0], color[1], color[2], 1.0)
                props.cells[empty_idx].is_set = True
                existing_colors.append((empty_idx, color))
                added_count += 1

            if added_count > 0:
                props.needs_bake = True

            save_color_grid_json(context)
        finally:
            set_skip_color_update(False)

        # Report results
        if duplicate_infos:
            for info in duplicate_infos:
                self.report({'INFO'}, f"Duplicate: {info}")

        self.report({'INFO'}, f"Added {added_count} colors from {len(material_colors)} materials")
        return {'FINISHED'}

    def _linear_to_srgb(self, value):
        """Convert linear color value to sRGB"""
        value = max(0.0, min(1.0, value))
        if value <= 0.0031308:
            return value * 12.92
        else:
            return 1.055 * (value ** (1.0 / 2.4)) - 0.055

    def _get_base_color(self, material):
        """Extract base color from material (converted to sRGB)"""
        linear_color = None

        # Try node-based material first
        if material.use_nodes and material.node_tree:
            for node in material.node_tree.nodes:
                # Principled BSDF
                if node.type == 'BSDF_PRINCIPLED':
                    base_color_input = node.inputs.get('Base Color')
                    if base_color_input and not base_color_input.is_linked:
                        color = base_color_input.default_value
                        linear_color = (color[0], color[1], color[2])
                        break

                # Diffuse BSDF
                elif node.type == 'BSDF_DIFFUSE':
                    color_input = node.inputs.get('Color')
                    if color_input and not color_input.is_linked:
                        color = color_input.default_value
                        linear_color = (color[0], color[1], color[2])
                        break

        # Fallback to viewport color
        if linear_color is None and hasattr(material, 'diffuse_color'):
            color = material.diffuse_color
            linear_color = (color[0], color[1], color[2])

        if linear_color is None:
            return None

        # Convert linear to sRGB for display-referred color grid
        return (
            self._linear_to_srgb(linear_color[0]),
            self._linear_to_srgb(linear_color[1]),
            self._linear_to_srgb(linear_color[2])
        )


class COLORGRID_OT_open_image(bpy.types.Operator):
    """Open the baked color map in an image editor"""
    bl_idname = "colorgrid.open_image"
    bl_label = "Open in Image Editor"

    def execute(self, context):
        props = context.scene.color_grid
        output_path = bpy.path.abspath(props.output_path)

        if not output_path or not os.path.exists(output_path):
            self.report({'WARNING'}, "Image file not found. Bake first.")
            return {'CANCELLED'}

        # Load or get existing image
        img_name = os.path.basename(output_path)
        img = bpy.data.images.get(img_name)

        if img:
            img.reload()
        else:
            img = bpy.data.images.load(output_path)

        # Find existing image editor area
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                area.spaces.active.image = img
                self.report({'INFO'}, f"Opened: {img_name}")
                return {'FINISHED'}

        # No image editor found, try to split VIEW_3D
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                with context.temp_override(area=area):
                    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)

                for new_area in context.screen.areas:
                    if new_area.type == 'VIEW_3D' and new_area != area:
                        new_area.type = 'IMAGE_EDITOR'
                        new_area.spaces.active.image = img
                        break

                self.report({'INFO'}, f"Opened: {img_name}")
                return {'FINISHED'}

        self.report({'WARNING'}, "Could not open image editor")
        return {'CANCELLED'}


class COLORGRID_OT_open_uv(bpy.types.Operator):
    """Open the baked color map in a UV editor"""
    bl_idname = "colorgrid.open_uv"
    bl_label = "Open in UV Editor"

    def execute(self, context):
        props = context.scene.color_grid
        output_path = bpy.path.abspath(props.output_path)

        if not output_path or not os.path.exists(output_path):
            self.report({'WARNING'}, "Image file not found. Bake first.")
            return {'CANCELLED'}

        # Load or get existing image
        img_name = os.path.basename(output_path)
        img = bpy.data.images.get(img_name)

        if img:
            img.reload()
        else:
            img = bpy.data.images.load(output_path)

        # Find existing image editor area
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                space = area.spaces.active
                space.image = img
                space.mode = 'UV'
                self.report({'INFO'}, f"Opened in UV Editor: {img_name}")
                return {'FINISHED'}

        # No image editor found, try to split VIEW_3D
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                with context.temp_override(area=area):
                    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)

                for new_area in context.screen.areas:
                    if new_area.type == 'VIEW_3D' and new_area != area:
                        new_area.type = 'IMAGE_EDITOR'
                        space = new_area.spaces.active
                        space.image = img
                        space.mode = 'UV'
                        break

                self.report({'INFO'}, f"Opened in UV Editor: {img_name}")
                return {'FINISHED'}

        self.report({'WARNING'}, "Could not open UV Editor")
        return {'CANCELLED'}


class COLORGRID_OT_load_grid(bpy.types.Operator, ImportHelper):
    """Load color grid from an existing image or JSON file"""
    bl_idname = "colorgrid.load_grid"
    bl_label = "Load Color Grid"
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.png;*.jpg;*.jpeg;*.json",
        options={'HIDDEN'}
    )

    def execute(self, context):
        props = context.scene.color_grid

        # Push undo
        try:
            bpy.ops.ed.undo_push(message="Before Load Color Grid")
        except Exception:
            pass

        set_skip_color_update(True)
        try:
            filepath = self.filepath

            # Check if JSON file
            if filepath.lower().endswith('.json'):
                return self._load_from_json(context, filepath)
            else:
                return self._load_from_image(context, filepath)
        finally:
            set_skip_color_update(False)

    def _load_from_json(self, context, filepath):
        """Load grid from JSON metadata file"""
        props = context.scene.color_grid

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load JSON: {e}")
            return {'CANCELLED'}

        # Apply grid settings
        props.image_width = data.get('image_width', 1024)
        props.image_height = data.get('image_height', 1024)
        props.grid_cols = data.get('grid_cols', 4)
        props.grid_rows = data.get('grid_rows', 4)

        # Ensure cells exist
        target_count = props.grid_cols * props.grid_rows
        while len(props.cells) < target_count:
            props.cells.add()
        while len(props.cells) > target_count:
            props.cells.remove(len(props.cells) - 1)

        # Apply cell colors
        for cell_data in data.get('cells', []):
            row = cell_data.get('row', 0)
            col = cell_data.get('col', 0)
            idx = row * props.grid_cols + col

            if 0 <= idx < len(props.cells):
                props.cells[idx].color = (
                    cell_data.get('r', 0.0),
                    cell_data.get('g', 0.0),
                    cell_data.get('b', 0.0),
                    cell_data.get('a', 1.0)
                )
                props.cells[idx].is_set = cell_data.get('is_set', True)

        # Update output path to corresponding PNG
        props.output_path = os.path.splitext(filepath)[0] + '.png'

        self.report({'INFO'}, f"Loaded grid from: {os.path.basename(filepath)}")
        return {'FINISHED'}

    def _load_from_image(self, context, filepath):
        """Load grid by sampling average colors from image regions"""
        props = context.scene.color_grid

        # Check for companion JSON file to get is_set values
        json_path = os.path.splitext(filepath)[0] + '.json'
        json_is_set = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    for cell_data in json_data.get('cells', []):
                        row = cell_data.get('row', 0)
                        col = cell_data.get('col', 0)
                        json_is_set[(row, col)] = cell_data.get('is_set', False)
            except Exception:
                pass

        # Load image
        try:
            img = bpy.data.images.load(filepath)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load image: {e}")
            return {'CANCELLED'}

        img_width, img_height = img.size

        # Update image dimensions
        props.image_width = img_width
        props.image_height = img_height

        # Ensure cells exist
        target_count = props.grid_cols * props.grid_rows
        while len(props.cells) < target_count:
            props.cells.add()
        while len(props.cells) > target_count:
            props.cells.remove(len(props.cells) - 1)

        # Get pixel data
        pixels = list(img.pixels)

        # Calculate cell dimensions in the source image
        cell_width = img_width // props.grid_cols
        cell_height = img_height // props.grid_rows

        # Sample average color from each cell region
        for row in range(props.grid_rows):
            for col in range(props.grid_cols):
                cell_idx = row * props.grid_cols + col

                # Calculate pixel range for this cell
                x_start = col * cell_width
                x_end = (col + 1) * cell_width if col < props.grid_cols - 1 else img_width
                # Flip Y axis
                y_start = (props.grid_rows - 1 - row) * cell_height
                y_end = (props.grid_rows - row) * cell_height if row > 0 else img_height

                # Accumulate colors
                r_sum, g_sum, b_sum, a_sum = 0.0, 0.0, 0.0, 0.0
                pixel_count = 0

                for y in range(y_start, y_end):
                    for x in range(x_start, x_end):
                        pixel_idx = (y * img_width + x) * 4
                        r_sum += pixels[pixel_idx]
                        g_sum += pixels[pixel_idx + 1]
                        b_sum += pixels[pixel_idx + 2]
                        a_sum += pixels[pixel_idx + 3] if len(pixels) > pixel_idx + 3 else 1.0
                        pixel_count += 1

                # Calculate average
                if pixel_count > 0:
                    r = r_sum / pixel_count
                    g = g_sum / pixel_count
                    b = b_sum / pixel_count
                    a = a_sum / pixel_count
                else:
                    r, g, b, a = 0.0, 0.0, 0.0, 1.0

                # Apply to cell
                props.cells[cell_idx].color = (r, g, b, a)

                # Use is_set from JSON if available, otherwise check if not black
                if json_is_set:
                    props.cells[cell_idx].is_set = json_is_set.get((row, col), False)
                else:
                    # If no JSON, consider non-black colors as "set"
                    is_black = (r < 0.01 and g < 0.01 and b < 0.01)
                    props.cells[cell_idx].is_set = not is_black

        # Update output path
        props.output_path = filepath

        # Remove loaded image
        bpy.data.images.remove(img)

        self.report({'INFO'}, f"Loaded colors from: {os.path.basename(filepath)}")
        return {'FINISHED'}


class COLORGRID_OT_create_material(bpy.types.Operator):
    """Create a new material with the color map image connected"""
    bl_idname = "colorgrid.create_material"
    bl_label = "Create Color Material"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.color_grid
        return props.output_path and context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        props = context.scene.color_grid
        obj = context.active_object

        # Get output path
        output_path = bpy.path.abspath(props.output_path)
        if not output_path:
            self.report({'ERROR'}, "Output path not set")
            return {'CANCELLED'}

        # Check if image exists
        if not os.path.exists(output_path):
            self.report({'ERROR'}, f"Image not found: {output_path}. Bake the color map first.")
            return {'CANCELLED'}

        # Push undo
        try:
            bpy.ops.ed.undo_push(message="Before Create Color Material")
        except Exception:
            pass

        # Get or load the image
        img_name = os.path.basename(output_path)
        img = bpy.data.images.get(img_name)

        if img:
            img.reload()
        else:
            img = bpy.data.images.load(output_path)

        # Create new material
        mat_name = "Color_Map"
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True

        # Get node tree
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear default nodes
        nodes.clear()

        # Create Principled BSDF
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (0, 0)

        # Create Image Texture node
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.location = (-300, 0)
        tex_node.image = img

        # Create Material Output
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (300, 0)

        # Link Image Texture to Principled BSDF Base Color
        links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])

        # Link Principled BSDF to Material Output
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])

        # Add material to object
        if obj.data.materials:
            obj.data.materials.append(mat)
        else:
            obj.data.materials.append(mat)

        # Set as active material
        obj.active_material_index = len(obj.data.materials) - 1

        self.report({'INFO'}, f"Created material '{mat_name}' with color map")
        return {'FINISHED'}


class COLORGRID_OT_auto_uv_layout(bpy.types.Operator):
    """Automatically layout UVs to match material colors with grid cells"""
    bl_idname = "colorgrid.auto_uv_layout"
    bl_label = "Auto UV Layout"
    bl_description = "Project UV and arrange to match material colors with grid cells"
    bl_options = {'REGISTER', 'UNDO'}

    uv_method: bpy.props.EnumProperty(
        name="UV Projection",
        description="UV projection method to use",
        items=[
            ('SMART', "Smart UV Project", "Use Smart UV Project"),
            ('CUBE', "Cube Projection", "Use Cube Projection"),
            ('CYLINDER', "Cylinder Projection", "Use Cylinder Projection"),
            ('SPHERE', "Sphere Projection", "Use Sphere Projection"),
            ('EXISTING', "Use Existing UV", "Keep existing UV, only rearrange"),
        ],
        default='SMART'
    )

    bake_first: bpy.props.BoolProperty(
        name="Bake Before UV Layout",
        description="Bake the color map before applying UV layout",
        default=True
    )

    @classmethod
    def poll(cls, context):
        props = context.scene.color_grid
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        # Grid must be initialized
        expected_cells = props.grid_cols * props.grid_rows
        return len(props.cells) == expected_cells

    def invoke(self, context, event):
        props = context.scene.color_grid
        # Check if bake is needed
        self._needs_bake = props.needs_bake
        self.bake_first = props.needs_bake
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout

        # Show warning if needs bake
        if hasattr(self, '_needs_bake') and self._needs_bake:
            box = layout.box()
            box.alert = True
            box.label(text="Grid has unsaved changes!", icon='ERROR')
            box.prop(self, "bake_first", text="Bake color map first")

        layout.prop(self, "uv_method")

    def execute(self, context):
        import bmesh

        props = context.scene.color_grid
        obj = context.active_object

        # Push undo
        try:
            bpy.ops.ed.undo_push(message="Before Auto UV Layout")
        except Exception:
            pass

        # Bake first if requested
        if self.bake_first and props.needs_bake:
            result = bpy.ops.colorgrid.bake_grid()
            if result != {'FINISHED'}:
                self.report({'ERROR'}, "Failed to bake color map")
                return {'CANCELLED'}

        # Store original mode
        original_mode = obj.mode

        # Go to object mode first
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Apply UV projection
        if self.uv_method != 'EXISTING':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')

            if self.uv_method == 'SMART':
                bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
            elif self.uv_method == 'CUBE':
                bpy.ops.uv.cube_project(cube_size=1.0)
            elif self.uv_method == 'CYLINDER':
                bpy.ops.uv.cylinder_project()
            elif self.uv_method == 'SPHERE':
                bpy.ops.uv.sphere_project()

            bpy.ops.object.mode_set(mode='OBJECT')

        # Load JSON to get cell colors
        output_path = bpy.path.abspath(props.output_path)
        json_path = os.path.splitext(output_path)[0] + '.json' if output_path else None

        # Build cell color lookup from props
        cell_colors = []
        for idx, cell in enumerate(props.cells):
            if cell.is_set:
                row = idx // props.grid_cols
                col = idx % props.grid_cols
                cell_colors.append({
                    'row': row,
                    'col': col,
                    'color': (cell.color[0], cell.color[1], cell.color[2])
                })

        if not cell_colors:
            self.report({'WARNING'}, "No colors set in grid")
            return {'CANCELLED'}

        # Get mesh data
        mesh = obj.data

        # Ensure we have UV layer
        if not mesh.uv_layers:
            mesh.uv_layers.new(name="UVMap")
        uv_layer = mesh.uv_layers.active

        # Build material color lookup
        material_colors = {}
        for mat_idx, mat in enumerate(mesh.materials):
            if mat is None:
                continue
            color = self._get_base_color_linear(mat)
            if color:
                material_colors[mat_idx] = color

        if not material_colors:
            self.report({'WARNING'}, "No materials with base color found")
            return {'CANCELLED'}

        # Match materials to grid cells
        material_to_cell = {}
        for mat_idx, mat_color in material_colors.items():
            best_cell = self._find_matching_cell(mat_color, cell_colors)
            if best_cell:
                material_to_cell[mat_idx] = best_cell

        if not material_to_cell:
            self.report({'WARNING'}, "No material colors matched grid cells")
            return {'CANCELLED'}

        # Use bmesh for UV manipulation
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()

        uv_layer_bm = bm.loops.layers.uv.verify()

        # Group faces by material
        faces_by_material = {}
        for face in bm.faces:
            mat_idx = face.material_index
            if mat_idx in material_to_cell:
                if mat_idx not in faces_by_material:
                    faces_by_material[mat_idx] = []
                faces_by_material[mat_idx].append(face)

        # Process each material group
        processed_count = 0
        for mat_idx, faces in faces_by_material.items():
            cell_info = material_to_cell[mat_idx]
            row = cell_info['row']
            col = cell_info['col']

            # Calculate cell UV bounds
            # UV coordinates: u goes 0-1 left to right, v goes 0-1 bottom to top
            cell_u_min = col / props.grid_cols
            cell_u_max = (col + 1) / props.grid_cols
            # Row 0 is top of grid, but in UV v=1 is top
            cell_v_max = 1.0 - (row / props.grid_rows)
            cell_v_min = 1.0 - ((row + 1) / props.grid_rows)

            # Add small margin inside cell
            margin = 0.02
            cell_u_min += margin
            cell_u_max -= margin
            cell_v_min += margin
            cell_v_max -= margin

            # Collect all UV coordinates for this material's faces
            all_uvs = []
            for face in faces:
                for loop in face.loops:
                    uv = loop[uv_layer_bm].uv
                    all_uvs.append(uv)

            if not all_uvs:
                continue

            # Find current UV bounds
            u_min = min(uv.x for uv in all_uvs)
            u_max = max(uv.x for uv in all_uvs)
            v_min = min(uv.y for uv in all_uvs)
            v_max = max(uv.y for uv in all_uvs)

            current_width = u_max - u_min
            current_height = v_max - v_min

            # Calculate scale to fit in cell (maintaining aspect ratio)
            cell_width = cell_u_max - cell_u_min
            cell_height = cell_v_max - cell_v_min

            if current_width > 0 and current_height > 0:
                scale_u = cell_width / current_width
                scale_v = cell_height / current_height
                scale = min(scale_u, scale_v)  # Uniform scale to maintain aspect
            else:
                scale = 1.0

            # Calculate center offset
            current_center_u = (u_min + u_max) / 2
            current_center_v = (v_min + v_max) / 2
            cell_center_u = (cell_u_min + cell_u_max) / 2
            cell_center_v = (cell_v_min + cell_v_max) / 2

            # Transform all UVs
            for face in faces:
                for loop in face.loops:
                    uv = loop[uv_layer_bm].uv
                    # Scale around center
                    new_u = (uv.x - current_center_u) * scale + cell_center_u
                    new_v = (uv.y - current_center_v) * scale + cell_center_v
                    uv.x = new_u
                    uv.y = new_v

            processed_count += len(faces)

        # Write back to mesh
        bm.to_mesh(mesh)
        bm.free()

        # Store old materials for removal
        old_materials = [mat for mat in mesh.materials if mat is not None]

        # Clear all material slots
        mesh.materials.clear()

        # Create new color material
        output_path = bpy.path.abspath(props.output_path)
        if output_path and os.path.exists(output_path):
            # Get or load the image
            img_name = os.path.basename(output_path)
            img = bpy.data.images.get(img_name)

            if img:
                img.reload()
            else:
                img = bpy.data.images.load(output_path)

            # Create new material
            mat_name = "Color_Map"
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True

            # Get node tree
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            # Clear default nodes
            nodes.clear()

            # Create Principled BSDF
            principled = nodes.new('ShaderNodeBsdfPrincipled')
            principled.location = (0, 0)

            # Create Image Texture node
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.location = (-300, 0)
            tex_node.image = img

            # Create Material Output
            output_node = nodes.new('ShaderNodeOutputMaterial')
            output_node.location = (300, 0)

            # Link Image Texture to Principled BSDF Base Color
            links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])

            # Link Principled BSDF to Material Output
            links.new(principled.outputs['BSDF'], output_node.inputs['Surface'])

            # Add material to object
            mesh.materials.append(mat)

        # Remove old materials that are no longer used by any object
        for old_mat in old_materials:
            if old_mat.users == 0:
                bpy.data.materials.remove(old_mat)

        # Restore original mode
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=original_mode)

        # Open UV Editor with the baked image
        self._open_uv_editor(context)

        self.report({'INFO'}, f"UV layout complete: {processed_count} faces processed, {len(material_to_cell)} materials matched")
        return {'FINISHED'}

    def _open_uv_editor(self, context):
        """Open UV Editor with the color map image"""
        props = context.scene.color_grid
        output_path = bpy.path.abspath(props.output_path)

        if not output_path or not os.path.exists(output_path):
            return

        # Get or load the image
        img_name = os.path.basename(output_path)
        img = bpy.data.images.get(img_name)
        if not img:
            try:
                img = bpy.data.images.load(output_path)
            except Exception:
                return

        # Find existing image editor area
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                space = area.spaces.active
                space.image = img
                space.mode = 'UV'
                return

        # No image editor found, try to split VIEW_3D
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                with context.temp_override(area=area):
                    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)

                for new_area in context.screen.areas:
                    if new_area.type == 'VIEW_3D' and new_area != area:
                        new_area.type = 'IMAGE_EDITOR'
                        space = new_area.spaces.active
                        space.image = img
                        space.mode = 'UV'
                        break
                return

    def _get_base_color_linear(self, material):
        """Extract base color from material in linear color space"""
        if material.use_nodes and material.node_tree:
            for node in material.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    base_color_input = node.inputs.get('Base Color')
                    if base_color_input and not base_color_input.is_linked:
                        color = base_color_input.default_value
                        return (color[0], color[1], color[2])
                elif node.type == 'BSDF_DIFFUSE':
                    color_input = node.inputs.get('Color')
                    if color_input and not color_input.is_linked:
                        color = color_input.default_value
                        return (color[0], color[1], color[2])

        if hasattr(material, 'diffuse_color'):
            color = material.diffuse_color
            return (color[0], color[1], color[2])

        return None

    def _linear_to_srgb(self, value):
        """Convert linear color value to sRGB"""
        value = max(0.0, min(1.0, value))
        if value <= 0.0031308:
            return value * 12.92
        else:
            return 1.055 * (value ** (1.0 / 2.4)) - 0.055

    def _find_matching_cell(self, mat_color_linear, cell_colors, tolerance=0.05):
        """Find grid cell matching material color"""
        # Convert material color from linear to sRGB for comparison
        mat_color_srgb = (
            self._linear_to_srgb(mat_color_linear[0]),
            self._linear_to_srgb(mat_color_linear[1]),
            self._linear_to_srgb(mat_color_linear[2])
        )

        best_match = None
        best_distance = float('inf')

        for cell in cell_colors:
            cell_color = cell['color']
            # Calculate color distance
            distance = (
                (mat_color_srgb[0] - cell_color[0]) ** 2 +
                (mat_color_srgb[1] - cell_color[1]) ** 2 +
                (mat_color_srgb[2] - cell_color[2]) ** 2
            ) ** 0.5

            if distance < best_distance:
                best_distance = distance
                best_match = cell

        # Only return if within tolerance
        if best_distance <= tolerance * 1.732:  # sqrt(3) for max RGB distance
            return best_match

        return None


class COLORGRID_OT_quick_setup(bpy.types.Operator):
    """One-click setup: Import Material Colors → Bake Color Map → Auto UV Layout"""
    bl_idname = "colorgrid.quick_setup"
    bl_label = "Quick Setup"
    bl_description = "Import colors from materials, bake color map, and auto layout UVs in one click"
    bl_options = {'REGISTER', 'UNDO'}

    uv_method: bpy.props.EnumProperty(
        name="UV Projection",
        description="UV projection method to use",
        items=[
            ('SMART', "Smart UV Project", "Use Smart UV Project"),
            ('CUBE', "Cube Projection", "Use Cube Projection"),
            ('CYLINDER', "Cylinder Projection", "Use Cylinder Projection"),
            ('SPHERE', "Sphere Projection", "Use Sphere Projection"),
            ('EXISTING', "Use Existing UV", "Keep existing UV, only rearrange"),
        ],
        default='SMART'
    )

    @classmethod
    def poll(cls, context):
        props = context.scene.color_grid
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        # Grid must be initialized
        expected_cells = props.grid_cols * props.grid_rows
        if len(props.cells) != expected_cells:
            return False
        # Must have materials
        return len(obj.data.materials) > 0

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Quick Setup will:", icon='INFO')
        col = box.column(align=True)
        col.label(text="1. Import Material Colors")
        col.label(text="2. Bake Color Map")
        col.label(text="3. Auto UV Layout")

        layout.separator()
        layout.prop(self, "uv_method")

    def execute(self, context):
        props = context.scene.color_grid

        # Push undo
        try:
            bpy.ops.ed.undo_push(message="Before Quick Setup")
        except Exception:
            pass

        # Step 1: Import Material Colors
        result = bpy.ops.colorgrid.import_material_colors()
        if result != {'FINISHED'}:
            self.report({'WARNING'}, "Import Material Colors had issues, continuing...")

        # Step 2: Bake Color Map
        result = bpy.ops.colorgrid.bake_grid()
        if result != {'FINISHED'}:
            self.report({'ERROR'}, "Failed to bake color map")
            return {'CANCELLED'}

        # Step 3: Auto UV Layout (with bake_first=False since we just baked)
        result = bpy.ops.colorgrid.auto_uv_layout(uv_method=self.uv_method, bake_first=False)
        if result != {'FINISHED'}:
            self.report({'ERROR'}, "Failed to apply UV layout")
            return {'CANCELLED'}

        self.report({'INFO'}, "Quick Setup complete!")
        return {'FINISHED'}


class COLORGRID_OT_open_folder(bpy.types.Operator):
    """Open the output folder in file explorer"""
    bl_idname = "colorgrid.open_folder"
    bl_label = "Open Output Folder"

    @classmethod
    def poll(cls, context):
        props = context.scene.color_grid
        return props.output_path

    def execute(self, context):
        import subprocess
        import platform

        props = context.scene.color_grid
        output_path = bpy.path.abspath(props.output_path)

        if not output_path:
            self.report({'ERROR'}, "Output path not set")
            return {'CANCELLED'}

        # Get folder path
        folder_path = os.path.dirname(output_path)

        if not folder_path or not os.path.exists(folder_path):
            self.report({'ERROR'}, f"Folder does not exist: {folder_path}")
            return {'CANCELLED'}

        # Open folder in file explorer
        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(folder_path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', folder_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])

            self.report({'INFO'}, f"Opened folder: {folder_path}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open folder: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


classes = (
    COLORGRID_OT_init_grid,
    COLORGRID_OT_set_cell_color,
    COLORGRID_OT_clear_cell,
    COLORGRID_OT_edit_grid_cell,
    COLORGRID_OT_fill_grid,
    COLORGRID_OT_randomize_grid,
    COLORGRID_OT_clear_grid,
    COLORGRID_OT_bake_grid,
    COLORGRID_OT_import_material_colors,
    COLORGRID_OT_open_image,
    COLORGRID_OT_open_uv,
    COLORGRID_OT_load_grid,
    COLORGRID_OT_create_material,
    COLORGRID_OT_auto_uv_layout,
    COLORGRID_OT_quick_setup,
    COLORGRID_OT_open_folder,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
