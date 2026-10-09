"""Capture the opening animation as a PNG sequence from Blender's viewport.

Set EXPORT_FRAMES, EXPORT_DIR, and EXPORT_WIDTH in the execution namespace
to capture a small pose review. Defaults capture all 120 frames at 1280 px.
"""

import bpy
import json
from pathlib import Path

scene=bpy.data.scenes['04_Opening_animation']
bpy.context.window.scene=scene
queue=list(globals().get('EXPORT_FRAMES',range(1,121)))
output=Path(globals().get('EXPORT_DIR','/tmp/wearable-leash-pod-animation-frames'))
output.mkdir(parents=True,exist_ok=True)
width=globals().get('EXPORT_WIDTH',1280)
scene.render.resolution_x=width
scene.render.resolution_y=width*3//4
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
captured=[]
current=None

def set_frame():
    global current
    if not queue:
        scene.frame_set(1)
        scene.render.resolution_x=1280
        scene.render.resolution_y=960
        scene.render.filepath=str(Path(bpy.data.filepath).parent/'opening-frame.png')
        (output/'complete.json').write_text(json.dumps({'frames':captured,'fps':24,'width':width}))
        print('ANIMATION_EXPORT_COMPLETE '+str(output),flush=True)
        return None
    current=queue.pop(0)
    scene.frame_set(current)
    bpy.context.view_layer.update()
    area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
    space=area.spaces.active
    space.overlay.show_overlays=False
    space.show_gizmo=False
    space.shading.type='MATERIAL'
    space.shading.use_scene_world=True
    space.shading.use_scene_lights=True
    space.region_3d.view_perspective='CAMERA'
    scene.render.filepath=str(output/f'frame_{current:04d}.png')
    area.tag_redraw()
    bpy.app.timers.register(capture,first_interval=.25)
    return None

def capture():
    area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
    region=next(r for r in area.regions if r.type=='WINDOW')
    with bpy.context.temp_override(area=area,region=region):
        bpy.ops.render.opengl(write_still=True,view_context=True)
    captured.append(current)
    if current%24==0:
        print('ANIMATION_FRAME '+str(current),flush=True)
    bpy.app.timers.register(set_frame,first_interval=.03)
    return None

bpy.app.timers.register(set_frame,first_interval=1)
