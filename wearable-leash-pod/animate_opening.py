"""Add a five-second pull-to-release animation to the static product model."""

import bpy
import math
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'assets'
scene_name = '04_Opening_animation'
if scene_name in bpy.data.scenes:
    raise RuntimeError('The opening animation scene already exists')

scene = bpy.data.scenes.new(scene_name)
for name in ['Pod','Latch','Leash','Harness','Lights','Cameras']:
    scene.collection.children.link(bpy.data.collections[name])
groups = {}
copies = {}
for name in ['Pod','Latch','Leash']:
    col = bpy.data.collections.new(name+'_Animation')
    bpy.data.collections[name].children.link(col)
    groups[name] = col
    for original in bpy.data.collections[name+'_Closed'].objects:
        obj = original.copy()
        obj.data = original.data.copy()
        obj.animation_data_clear()
        obj.name = original.name.replace('_Closed_', '_Animation_')
        obj.data.name = obj.name+'_geometry'
        col.objects.link(obj)
        copies[original.name] = obj

# Exclude animation geometry from the saved static views.
for sc in list(bpy.data.scenes):
    bpy.context.window.scene = sc
    bpy.context.view_layer.update()
    for name in ['Pod','Latch','Leash']:
        layer = sc.view_layers[0].layer_collection.children[name]
        for child in layer.children:
            if sc == scene:
                child.exclude = child.name != name+'_Animation'
            elif child.name == name+'_Animation':
                child.exclude = True

bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .001
scene.unit_settings.length_unit = 'MILLIMETERS'
scene.world = bpy.data.scenes['01_Closed'].world
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_samples = 64
scene.eevee.taa_render_samples = 64
scene.eevee.shadow_ray_count = 4
scene.render.resolution_x = 1280
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 120
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = -1.3

def key(obj, path, frame):
    obj.keyframe_insert(data_path=path, frame=frame)

def ribbon_centers(obj):
    verts = obj.data.vertices
    return [(verts[i].co+verts[i+1].co)*.5 for i in range(0,len(verts),2)]

def resample(points, count):
    pts = [Vector(p) for p in points]
    distances = [0]
    for a,b in zip(pts,pts[1:]):
        distances.append(distances[-1]+(b-a).length)
    result=[]
    segment=0
    for i in range(count):
        distance=distances[-1]*i/(count-1)
        while segment<len(pts)-2 and distances[segment+1]<distance:
            segment+=1
        length=distances[segment+1]-distances[segment]
        t=(distance-distances[segment])/length if length else 0
        result.append(pts[segment].lerp(pts[segment+1],t))
    return result

def ribbon_object(name, points, width, mat):
    verts=[p+Vector((0,y,0)) for p in points for y in [-width/2,width/2]]
    faces=[(i*2,i*2+2,i*2+3,i*2+1) for i in range(len(points)-1)]
    mesh=bpy.data.meshes.new(name+'_geometry')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    groups['Leash'].objects.link(obj)
    mesh.materials.append(mat)
    for face in mesh.polygons:
        face.use_smooth=True
    mod=obj.modifiers.new('Woven strap thickness','SOLIDIFY')
    mod.thickness=.7
    mod.offset=0
    mod=obj.modifiers.new('Soft textile edges','BEVEL')
    mod.width=.16
    mod.segments=3
    return obj

# Lid mesh coordinates use millimeters in world space. Shift them to the hinge.
pivot=Vector((-30,0,28.3))
hinge=bpy.data.objects.new('Pod_Animation_hinge_pivot',None)
groups['Pod'].objects.link(hinge)
hinge.location=pivot
lid=copies['Pod_Closed_spring_lid']
lid.data.transform(Matrix.Translation(-pivot))
lid.parent=hinge
lid.location=(0,0,0)
led=copies['Pod_Closed_green_LED_3mm']
led.parent=hinge
led.location-=pivot
for frame,angle in [(1,0),(32,0),(38,-20),(47,-83),(54,-108),(62,-101),(70,-104),(120,-104)]:
    hinge.rotation_euler.y=math.radians(angle)
    key(hinge,'rotation_euler',frame)

# The mechanism stays under the interior cover in this exterior view.
for obj in groups['Latch'].objects:
    obj.hide_render=True
    obj.hide_set(True)
    base_location=obj.location.copy()
    if any(term in obj.name for term in ['sear_lift_stem','sear_retaining_pin','cam_follower','shared_sear_lift_bridge','sear_bridge_end']):
        for frame,z in [(1,0),(27,0),(33,2.8),(120,2.8)]:
            obj.location.z=base_location.z+z
            key(obj,'location',frame)
    if 'axial_ramp_cam' in obj.name:
        for frame,x in [(1,0),(25,0),(33,3),(120,3)]:
            obj.location.x=base_location.x+x
            key(obj,'location',frame)

# A small axial movement precedes the release.
handle=copies['Leash_Closed_orange_handle_loop_16mm']
handle.shape_key_add(name='Stowed')
free=handle.shape_key_add(name='Released loop')
count=len(handle.data.vertices)//2
for i in range(count):
    t=-math.pi/2+2*math.pi*i/count
    center=Vector((89+20*math.cos(t),-38,6.5+5.2*math.sin(t)))
    free.data[2*i].co=center+Vector((0,-8,0))
    free.data[2*i+1].co=center+Vector((0,8,0))
for frame,x,z in [(1,0,0),(22,0,0),(32,4.5,0),(39,5,4),(53,3,20),(66,1,12),(84,0,0),(120,0,0)]:
    handle.location=(x,0,z)
    key(handle,'location',frame)
for frame,value in [(1,0),(34,0),(43,.12),(56,.5),(72,.87),(86,1),(120,1)]:
    free.value=value
    key(free,'value',frame)

# One continuous ribbon morphs from the stored folds into the released path.
old_fold=copies['Leash_Closed_accordion_stack_150mm']
folded=ribbon_centers(old_fold)
stowed=[Vector(p) for p in [(39,0,11),(34,0,12),(27,0,12.7),(12,0,12.8),(2,0,13.5),(-24,0,13.5)]]
stowed+=folded[1:]
stowed += [Vector((-20,0,25)),Vector((-24,0,23.9))]
released=ribbon_centers(bpy.data.objects['Leash_Released_spilled_webbing_20mm'])
stowed=resample(stowed,220)
released=resample(released,220)
webbing=ribbon_object('Leash_Animation_unfolding_webbing',stowed,20,old_fold.data.materials[0])
webbing.shape_key_add(name='Accordion folds')
payout=webbing.shape_key_add(name='Spilled webbing')
for i,point in enumerate(released):
    payout.data[2*i].co=point+Vector((0,-10,0))
    payout.data[2*i+1].co=point+Vector((0,10,0))
for frame,value in [(1,0),(34,0),(43,.12),(56,.5),(72,.87),(86,1),(120,1)]:
    payout.value=value
    key(payout,'value',frame)
webbing_lift=webbing.shape_key_add(name='Lift clear of the shell')
for i,point in enumerate(stowed):
    lift=20*(i/(len(stowed)-1))**1.8
    for side in range(2):
        webbing_lift.data[2*i+side].co=webbing.data.vertices[2*i+side].co+Vector((0,0,lift))
for frame,z in [(1,0),(22,0),(32,0),(39,4),(53,20),(66,12),(84,0),(120,0)]:
    webbing_lift.value=z/20
    key(webbing_lift,'value',frame)
for name in ['Leash_Closed_accordion_stack_150mm','Leash_Closed_attached_leash_tail']:
    bpy.data.objects.remove(copies[name],do_unlink=True)

join=copies['Leash_Closed_handle_join']
join.shape_key_add(name='Stored join')
join_free=join.shape_key_add(name='Released join')
join_points=[(70,-38,1.2),(71,-38,1.6),(73,-38,2.5),(74,-38,3)]
for i,point in enumerate(join_points):
    join_free.data[2*i].co=Vector(point)+Vector((0,-8,0))
    join_free.data[2*i+1].co=Vector(point)+Vector((0,8,0))
for frame,value in [(1,0),(34,0),(43,.12),(56,.5),(72,.87),(86,1),(120,1)]:
    join_free.value=value
    key(join_free,'value',frame)
join_lift=join.shape_key_add(name='Follow handle lift')
join_tug=join.shape_key_add(name='Follow axial tug')
for i,vertex in enumerate(join.data.vertices):
    join_lift.data[i].co=vertex.co+Vector((0,0,20))
    join_tug.data[i].co=vertex.co+Vector((5*(i//2)/3,0,0))
for frame,x,z in [(1,0,0),(22,0,0),(32,4.5,0),(39,5,4),(53,3,20),(66,1,12),(84,0,0),(120,0,0)]:
    join_lift.value=z/20
    key(join_lift,'value',frame)
    join_tug.value=x/5
    key(join_tug,'value',frame)

camera_data=bpy.data.cameras.new('CAM_opening')
camera=bpy.data.objects.new('CAM_opening',camera_data)
bpy.data.collections['Cameras'].objects.link(camera)
camera_data.type='ORTHO'
camera_data.clip_start=.1
camera_data.clip_end=3000
camera_data.passepartout_alpha=1
scene.camera=camera
for frame,position,target,scale in [
    (1,(105,-130,125),(0,0,14),145),
    (24,(105,-130,125),(0,0,14),145),
    (55,(135,-170,154),(25,-9,41),230),
    (120,(135,-170,154),(25,-9,41),230),
]:
    camera.location=position
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.ortho_scale=scale
    key(camera,'location',frame)
    key(camera,'rotation_euler',frame)
    key(camera_data,'ortho_scale',frame)

# Clamped handles keep the spring settle poses and camera motion predictable.
for action in bpy.data.actions:
    for layer in action.layers:
        for strip in layer.strips:
            if hasattr(strip,'channelbags'):
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for point in curve.keyframe_points:
                            point.interpolation='BEZIER'
                            point.handle_left_type='AUTO_CLAMPED'
                            point.handle_right_type='AUTO_CLAMPED'

for frame,name in [(1,'Closed'),(24,'Pull loop'),(33,'Sear releases'),(54,'Lid open'),(88,'Webbing settled')]:
    scene.timeline_markers.new(name,frame=frame)
scene['trigger']='Axial pull on the orange handle loop'
scene['motion']='Keyframed demonstration; no force or cloth simulation'
scene.frame_set(1)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.overlay.show_overlays=False
            space.show_gizmo=False
            space.clip_start=.1
            space.clip_end=3000
            space.shading.type='MATERIAL'
            space.shading.use_scene_lights=True
            space.shading.use_scene_world=True
            space.region_3d.view_perspective='CAMERA'
            space.region_3d.view_camera_zoom=5
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.ed.undo_push(message='Animate the orange handle releasing the pod')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'wearable-leash-pod-opening.blend'))
print('OPENING_ANIMATION_READY',flush=True)
