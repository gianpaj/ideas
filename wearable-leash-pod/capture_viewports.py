"""Run in Blender's UI to save one viewport image per scene camera."""

import bpy
from pathlib import Path

out = Path(bpy.data.filepath).parent
queue = list(sorted(bpy.data.scenes, key=lambda scene: scene.name))
current = None

def next_view():
    global current
    if not queue:
        bpy.context.window.scene = bpy.data.scenes['01_Closed']
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
        (out / 'viewport-capture-complete.txt').write_text('Three static camera viewport images saved.\n')
        return None
    current = queue.pop(0)
    bpy.context.window.scene = current
    area = next(area for area in bpy.context.screen.areas if area.type == 'VIEW_3D')
    space = area.spaces.active
    space.region_3d.view_perspective = 'CAMERA'
    space.region_3d.view_camera_zoom = 5
    space.overlay.show_overlays = False
    space.show_gizmo = False
    space.shading.type = 'MATERIAL'
    space.shading.use_scene_world = True
    space.shading.use_scene_lights = True
    current.render.filepath = str(out / (current.camera.name + '.png'))
    area.tag_redraw()
    bpy.app.timers.register(capture, first_interval=8)
    return None

def capture():
    area = next(area for area in bpy.context.screen.areas if area.type == 'VIEW_3D')
    region = next(region for region in area.regions if region.type == 'WINDOW')
    with bpy.context.temp_override(area=area, region=region):
        bpy.ops.render.opengl(write_still=True, view_context=True)
    print('VIEWPORT_SAVED ' + current.camera.name, flush=True)
    bpy.app.timers.register(next_view, first_interval=1)
    return None

bpy.app.timers.register(next_view, first_interval=3)
