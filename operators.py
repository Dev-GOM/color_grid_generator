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

        # Find or create image editor area
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                area.spaces.active.image = img
                self.report({'INFO'}, f"Opened: {img_name}")
                return {'FINISHED'}

        # No image editor found, try to split
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                with context.temp_override(area=area):
                    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
                break

        # Set the new area to image editor
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.type = 'IMAGE_EDITOR'
                area.spaces.active.image = img
                break

        self.report({'INFO'}, f"Opened: {img_name}")
        return {'FINISHED'}


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

        # Find or create UV editor area
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                space = area.spaces.active
                space.image = img
                space.mode = 'UV'
                self.report({'INFO'}, f"Opened in UV Editor: {img_name}")
                return {'FINISHED'}

        # No image editor found, try to split
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                with context.temp_override(area=area):
                    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
                break

        # Set the new area to UV editor
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.type = 'IMAGE_EDITOR'
                space = area.spaces.active
                space.image = img
                space.mode = 'UV'
                break

        self.report({'INFO'}, f"Opened in UV Editor: {img_name}")
        return {'FINISHED'}


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
    COLORGRID_OT_open_folder,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
