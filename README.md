# Color Grid Generator

A Blender extension for creating color map textures for Unity and other game engines.

## Features

- **Visual Grid Editor**: Edit colors directly in a visual grid interface
- **Color Picker**: Full color picker with RGB/Hex display
- **Material Import**: Import base colors from object materials automatically (with Linear to sRGB conversion)
- **Fill & Randomize**: Quick fill or randomize colors with overwrite protection for set cells
- **Bake to PNG**: Export color maps with automatic JSON metadata
- **Auto Backup**: Creates backup before overwriting existing images
- **Material Creation**: One-click material setup with color map connected to Principled BSDF
- **Auto UV Layout**: Automatically arrange UVs to match material colors with grid cells
- **Quick Setup**: One-click workflow (Import Colors → Bake → UV Layout)

## Requirements

- Blender 4.2.0 or later

## Installation

### From ZIP file
1. Download `color_grid_generator-x.x.x.zip`
2. In Blender: Edit → Preferences → Get Extensions
3. Click dropdown (top-right) → "Install from Disk..."
4. Select the downloaded ZIP file

### For Development (Symbolic Link)
```cmd
mklink /D "%APPDATA%\Blender Foundation\Blender\4.5\extensions\user_default\color_grid_generator" "D:\Work\color_grid_generator"
```

## Usage

1. Open the **Color Grid** tab in the N-Panel (View3D sidebar)
2. Set output image size (Width/Height) and grid size (Cols/Rows)
3. Click **Initialize** to create the grid
4. Edit colors:
   - Click color swatches to edit directly
   - Click cell buttons (✓/+) to open detailed color picker
   - Use **Import Material Colors** to import from selected object
   - Use **Fill** or **Randomize** for bulk operations
5. Set output path and click **Bake Color Map** to export
6. Use **Create Color Material** to create a material with the color map
7. Use **Auto UV Layout** to arrange object UVs to match material colors with grid cells

## Panel Overview

### Output Size
Set the width and height of the output PNG image.

### Grid Size
Set the number of columns and rows in the color grid.

### Color Grid
- **✓** button: Cell has been set
- **+** button: Cell is empty (default black)
- Click buttons to open color picker popup
- Click color swatches for direct editing

### Toolbar Icons
- **Import**: Load from existing PNG/JSON
- **Material**: Import colors from object materials
- **Fill**: Fill all cells with a single color
- **Random**: Randomize cell colors
- **Clear**: Reset all cells to black

### Output
- Set the output file path
- **Folder icon**: Open output folder in file explorer
- **Bake Color Map**: Export the color grid as PNG
- **Image Editor / UV Editor**: Open the baked image

### Material
- **Create Color Material**: Create a new material with the color map connected

### UV Layout
- **Quick Setup**: One-click workflow that performs Import Material Colors → Bake Color Map → Auto UV Layout
- **Auto UV Layout**: Automatically project UV and arrange faces to match material colors with grid cells
  - Supports multiple UV projection methods: Smart UV Project, Cube, Cylinder, Sphere, or use existing UV
  - Matches material base colors to grid cell colors
  - Scales and positions UV islands to fit within corresponding grid cells
  - Faces with the same material share the same cell position (overlapped)
  - Faces without materials are left unchanged

## File Outputs

When you bake the color map, two files are created:

1. **color_map.png**: The color grid image
2. **color_map.json**: Metadata including grid dimensions and cell colors

### JSON Format
```json
{
  "image_width": 1024,
  "image_height": 1024,
  "grid_cols": 4,
  "grid_rows": 4,
  "cells": [
    {"row": 0, "col": 0, "r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0, "is_set": true},
    ...
  ]
}
```

## License

GPL-3.0-or-later

## Author

DevGOM
