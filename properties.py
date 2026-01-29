import bpy
import os
import json
from bpy.props import (
    IntProperty, FloatVectorProperty, PointerProperty,
    CollectionProperty, StringProperty, BoolProperty
)

# Debounce state for JSON auto-save
_pending_json_save = False
_debounce_delay = 0.3  # seconds

# Flag to skip update callback (used by operators for undo support)
_skip_color_update = False

# Color picker editing session tracking for undo support
_editing_session_active = False
_session_cell_id = None  # Track which cell is being edited


def _end_editing_session_timer():
    """Timer to end the color editing session"""
    global _editing_session_active, _session_cell_id
    _editing_session_active = False
    _session_cell_id = None
    return None  # Don't repeat


def _schedule_end_of_session():
    """Schedule end of editing session after a delay"""
    # Cancel existing timer if registered
    if bpy.app.timers.is_registered(_end_editing_session_timer):
        bpy.app.timers.unregister(_end_editing_session_timer)

    # Schedule new timer (0.5 seconds after last change)
    bpy.app.timers.register(_end_editing_session_timer, first_interval=0.5)


def _debounced_save_timer():
    """Timer callback to perform the actual JSON save"""
    global _pending_json_save
    _pending_json_save = False

    # Get context and save
    context = bpy.context
    if context and hasattr(context, 'scene') and hasattr(context.scene, 'color_grid'):
        _save_color_grid_json_from_props(context, save_colors=False)

    return None  # Don't repeat


def _schedule_json_save():
    """Schedule a debounced JSON save"""
    global _pending_json_save

    # Cancel existing timer if pending
    if _pending_json_save:
        if bpy.app.timers.is_registered(_debounced_save_timer):
            bpy.app.timers.unregister(_debounced_save_timer)

    # Schedule new timer
    _pending_json_save = True
    bpy.app.timers.register(_debounced_save_timer, first_interval=_debounce_delay)


def _save_color_grid_json_from_props(context, save_colors=True):
    """Save color grid metadata to JSON file

    Args:
        context: Blender context
        save_colors: If True, save color values. If False, preserve existing colors in JSON.
    """
    props = context.scene.color_grid

    output_path = bpy.path.abspath(props.output_path)
    if not output_path:
        return

    json_path = os.path.splitext(output_path)[0] + '.json'

    output_dir = os.path.dirname(json_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception:
            return

    # Load existing JSON to preserve colors if needed
    existing_colors = {}
    if not save_colors and os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                for cell_data in existing_data.get('cells', []):
                    key = (cell_data.get('row', 0), cell_data.get('col', 0))
                    existing_colors[key] = {
                        'r': cell_data.get('r', 0.0),
                        'g': cell_data.get('g', 0.0),
                        'b': cell_data.get('b', 0.0),
                        'a': cell_data.get('a', 1.0)
                    }
        except Exception:
            pass

    cell_colors = []
    for idx, cell in enumerate(props.cells):
        row = idx // props.grid_cols
        col = idx % props.grid_cols

        if save_colors:
            # Save current colors
            cell_data = {
                'row': row,
                'col': col,
                'r': cell.color[0],
                'g': cell.color[1],
                'b': cell.color[2],
                'a': cell.color[3],
                'is_set': cell.is_set
            }
        else:
            # Preserve existing colors from JSON
            key = (row, col)
            if key in existing_colors:
                cell_data = {
                    'row': row,
                    'col': col,
                    'r': existing_colors[key]['r'],
                    'g': existing_colors[key]['g'],
                    'b': existing_colors[key]['b'],
                    'a': existing_colors[key]['a'],
                    'is_set': cell.is_set
                }
            else:
                # No existing color, use current
                cell_data = {
                    'row': row,
                    'col': col,
                    'r': cell.color[0],
                    'g': cell.color[1],
                    'b': cell.color[2],
                    'a': cell.color[3],
                    'is_set': cell.is_set
                }

        cell_colors.append(cell_data)

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


def _on_color_change(self, context):
    """Mark cell as set when color is changed by user"""
    global _skip_color_update, _editing_session_active, _session_cell_id

    if _skip_color_update:
        return

    # Get cell ID (using id() of the cell object)
    cell_id = id(self)

    # Check if this is a new editing session or a different cell
    if not _editing_session_active or _session_cell_id != cell_id:
        # New session - push undo state before making changes
        try:
            bpy.ops.ed.undo_push(message="Before Color Change")
        except Exception:
            pass  # undo_push might fail in some contexts

        _editing_session_active = True
        _session_cell_id = cell_id

    # Mark as set when color is changed via UI
    self.is_set = True

    # Mark grid as needing bake
    if hasattr(context, 'scene') and hasattr(context.scene, 'color_grid'):
        context.scene.color_grid.needs_bake = True

    # Schedule end of session (resets after 0.5s of no changes)
    _schedule_end_of_session()

    # Schedule debounced JSON save (only saves after user stops dragging)
    _schedule_json_save()


def set_skip_color_update(skip):
    """Set the skip flag for color update callback (for operator use)"""
    global _skip_color_update
    _skip_color_update = skip


class ColorGridCellItem(bpy.types.PropertyGroup):
    """Individual cell in the color grid"""

    is_set: BoolProperty(
        name="Is Set",
        description="Whether this cell has been explicitly set",
        default=False
    )

    color: FloatVectorProperty(
        name="Color",
        description="Cell color",
        subtype='COLOR_GAMMA',  # sRGB color space - matches UI display
        size=4,
        default=(0.0, 0.0, 0.0, 1.0),  # Black - Unity standard for unused areas
        min=0.0,
        max=1.0,
        update=_on_color_change
    )


class ColorGridProperties(bpy.types.PropertyGroup):
    """Properties for Color Grid Generator"""

    # Image dimensions
    image_width: IntProperty(
        name="Width",
        description="Output image width in pixels",
        default=1024,
        min=64,
        max=8192
    )

    image_height: IntProperty(
        name="Height",
        description="Output image height in pixels",
        default=1024,
        min=64,
        max=8192
    )

    # Grid dimensions
    grid_cols: IntProperty(
        name="Columns",
        description="Number of columns in the grid",
        default=4,
        min=1,
        max=16,
        update=lambda self, ctx: _update_grid_cells(self, ctx)
    )

    grid_rows: IntProperty(
        name="Rows",
        description="Number of rows in the grid",
        default=4,
        min=1,
        max=16,
        update=lambda self, ctx: _update_grid_cells(self, ctx)
    )

    # Grid cells collection
    cells: CollectionProperty(
        type=ColorGridCellItem,
        name="Cells",
        description="Grid cell colors"
    )

    # Output path
    output_path: StringProperty(
        name="Output Path",
        description="Path to save the color map PNG",
        subtype='FILE_PATH',
        default="//Texture/color_map.png"
    )

    # UI state
    show_grid: BoolProperty(
        name="Show Grid",
        description="Show the color grid in the panel",
        default=True
    )

    # Bake state tracking
    needs_bake: BoolProperty(
        name="Needs Bake",
        description="Grid has been modified since last bake",
        default=False
    )


def _update_grid_cells(props, context):
    """Update cells collection when grid size changes"""
    target_count = props.grid_cols * props.grid_rows

    # Add cells if needed
    while len(props.cells) < target_count:
        props.cells.add()

    # Remove excess cells
    while len(props.cells) > target_count:
        props.cells.remove(len(props.cells) - 1)


classes = (
    ColorGridCellItem,
    ColorGridProperties,
)


def register():
    """Register color grid properties"""
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.color_grid = PointerProperty(type=ColorGridProperties)


def unregister():
    """Unregister color grid properties"""
    if hasattr(bpy.types.Scene, 'color_grid'):
        del bpy.types.Scene.color_grid
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
