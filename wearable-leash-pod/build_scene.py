"""Build the millimeter-scale pod and its three static camera states."""

import bpy
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'assets'
OUT.mkdir(exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for scene in list(bpy.data.scenes)[1:]:
    bpy.data.scenes.remove(scene)
for col in list(bpy.data.collections):
    bpy.data.collections.remove(col)

scene = bpy.context.scene
scene.name = '01_Closed'
groups = {}
for name in ['Pod', 'Latch', 'Leash', 'Harness', 'Lights', 'Cameras']:
    groups[name] = bpy.data.collections.new(name)
    scene.collection.children.link(groups[name])

states = ['Closed', 'Cutaway', 'Released']
parts = {}
for group in ['Pod', 'Latch', 'Leash']:
    for state in states:
        col = bpy.data.collections.new(group + '_' + state)
        groups[group].children.link(col)
        parts[group, state] = col

def color(hex_value):
    rgb = [int(hex_value[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v < .04045 else ((v+.055)/1.055)**2.4 for v in rgb) + (1,)

def material(name, hex_value, roughness, metallic=0, textile=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color(hex_value)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color(hex_value)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    if textile:
        bsdf.inputs['Sheen Weight'].default_value = .18
        tex = nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 210
        tex.inputs['Detail'].default_value = 2
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .22
        bump.inputs['Distance'].default_value = .07
        links.new(tex.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return mat

pod_mat = material('TPU | charcoal #2B2B2B', '2B2B2B', .55)
orange = material('Nylon | high-vis #FF5A1F', 'FF5A1F', .34, textile=True)
grey = material('Webbing | grey woven nylon', '777D80', .86, textile=True)
black = material('Harness | black webbing', '161819', .85, textile=True)
stitch = material('Thread | charcoal', '343839', .9)
steel = material('Latch | brushed stainless', 'B4BEC4', .31, .9)
steel.node_tree.nodes.get('Principled BSDF').inputs['Anisotropic'].default_value = .4
dark_metal = material('Solenoid | dark steel', '333C40', .38, .8)
copper = material('Solenoid | copper band', 'BC7748', .32, .75)
inner_mat = material('Latch | graphite guide', '444D51', .53)
ground_mat = material('Studio | warm grey', 'B8B5AF', .85)
green = material('LED | green lens', '34D774', .23)
green.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value = color('34D774')
green.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value = .65

def finish(obj, name, col, mat=None):
    obj.name = name
    obj.data.name = name + '_geometry'
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj

def mesh(name, verts, faces, col, mat):
    data = bpy.data.meshes.new(name + '_geometry')
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    if mat:
        data.materials.append(mat)
    return obj

def smooth(obj):
    for face in obj.data.polygons:
        face.use_smooth = True
    mod = obj.modifiers.new('Area weighted surface normals', 'WEIGHTED_NORMAL')
    mod.keep_sharp = True
    mod.weight = 40
    return obj

def bevel(obj, amount=.25, segments=3):
    mod = obj.modifiers.new('Soft manufactured edges', 'BEVEL')
    mod.width = amount
    mod.segments = segments
    return obj

def apply_modifier(obj, mod):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)

def box(name, loc, dims, col, mat, radius=.4):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = finish(bpy.context.object, name, col, mat)
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if radius:
        bevel(obj, radius, 4)
        smooth(obj)
    return obj

def rounded_outline(length, width, radius, samples=20):
    points = []
    for cx, cy, start in [(length/2-radius, width/2-radius, 0),
                          (-length/2+radius, width/2-radius, 90),
                          (-length/2+radius, -width/2+radius, 180),
                          (length/2-radius, -width/2+radius, 270)]:
        for i in range(samples+1):
            a = math.radians(start+i*90/samples)
            points.append((cx+radius*math.cos(a), cy+radius*math.sin(a)))
    return points

def rounded(name, loc, dims, radius, col, mat, bottom=.4, top=.4):
    length, width, height = dims
    rings = []
    steps = 8
    if bottom:
        for i in range(steps+1):
            a = math.pi*.5*i/steps
            rings.append((-height/2+bottom-bottom*math.cos(a), bottom*(1-math.sin(a))))
    else:
        rings.append((-height/2, 0))
    if top:
        for i in range(steps+1):
            a = math.pi*.5*i/steps
            rings.append((height/2-top+top*math.sin(a), top*(1-math.cos(a))))
    else:
        rings.append((height/2, 0))
    verts = []
    for z, inset in rings:
        verts.extend([(x+loc[0], y+loc[1], z+loc[2]) for x,y in rounded_outline(length-2*inset, width-2*inset, max(.05, radius-inset))])
    n = len(verts)//len(rings)
    faces = [tuple(reversed(range(n)))]
    for j in range(len(rings)-1):
        for i in range(n):
            a = j*n+i
            b = j*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
    faces.append(tuple(range((len(rings)-1)*n,len(rings)*n)))
    obj = mesh(name, verts, faces, col, mat)
    smooth(obj)
    return obj

def subtract(obj, cutter):
    mod = obj.modifiers.new('Machined cavity', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    apply_modifier(obj, mod)
    bpy.data.objects.remove(cutter, do_unlink=True)

def cylinder(name, a, b, radius, col, mat):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=(b-a).length, location=(a+b)/2)
    obj = finish(bpy.context.object, name, col, mat)
    obj.rotation_euler = (b-a).to_track_quat('Z','Y').to_euler()
    bevel(obj, .12, 3)
    smooth(obj)
    return obj

def tube(name, points, radius, col, mat, cyclic=False):
    data = bpy.data.curves.new(name+'_geometry', 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 20
    data.bevel_depth = radius
    data.bevel_resolution = 4
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for p, co in zip(spline.points, points):
        p.co = (*co,1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name,data)
    col.objects.link(obj)
    data.materials.append(mat)
    return obj

def ribbon(name, points, width, col, mat, lateral=(0,1,0), thickness=.55, cyclic=False):
    side = Vector(lateral).normalized()*width/2
    verts = []
    for p in points:
        p = Vector(p)
        verts.extend([p-side,p+side])
    count = len(points) if cyclic else len(points)-1
    faces = [(2*i, 2*((i+1)%len(points)), 2*((i+1)%len(points))+1,2*i+1) for i in range(count)]
    obj = mesh(name, verts, faces, col, mat)
    mod = obj.modifiers.new('Woven strap thickness', 'SOLIDIFY')
    mod.thickness = thickness
    mod.offset = 0
    bevel(obj, .16, 3)
    for face in obj.data.polygons:
        face.use_smooth = True
    obj['strap_width_mm'] = width
    return obj

def soften_path(points, steps=10):
    pts = [Vector(p) for p in points]
    result = []
    for i in range(len(pts)-1):
        a,b,c,d = pts[max(0,i-1)],pts[i],pts[i+1],pts[min(len(pts)-1,i+2)]
        for j in range(steps):
            t = j/steps
            result.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return result+[pts[-1]]

def copy_to(obj, state, group):
    new = obj.copy()
    new.data = obj.data.copy()
    new.name = obj.name.replace('Closed', state)
    new.data.name = new.name+'_geometry'
    parts[group,state].objects.link(new)
    return new

def transform_geometry(obj, matrix):
    if obj.type == 'MESH':
        obj.data.transform(matrix)
    else:
        obj.matrix_world = matrix @ obj.matrix_world

# The harness is shared by every scene.
harness = groups['Harness']
ribbon('Harness_dorsal_strap_22mm', [(-54,0,4),(-46,0,7),(-34,0,8),(34,0,8),(46,0,7),(54,0,4)],22,harness,black,thickness=1.4)
for x, label in [(-24,'rear'),(23,'front')]:
    points = [(x,-53+106*i/60,1.4+5.5*math.exp(-((-53+106*i/60)/27)**4)) for i in range(61)]
    ribbon('Harness_saddle_'+label,points,16,harness,black,lateral=(1,0,0),thickness=1.3)
    for side in [-1,1]:
        seam = [(p[0]+side*6.5,p[1],p[2]+.7) for p in points]
        tube('Harness_'+label+'_edge_stitch_'+str(side),seam,.085,harness,stitch)
for side in [-1,1]:
    tube('Harness_dorsal_edge_stitch_'+str(side),[(-46,side*9.3,7.8),(-34,side*9.3,8.8),(34,side*9.3,8.8),(46,side*9.3,7.8)],.09,harness,stitch)
ring = [(44+5*math.cos(t),7*math.sin(t),9.6) for t in [i*2*math.pi/96 for i in range(96)]]
tube('Harness_dorsal_attachment_ring',ring,1.05,harness,dark_metal,True)
box('Harness_ring_keeper',(40,0,8.8),(6,20,1.8),harness,black,.65)

pc = parts['Pod','Closed']
body = rounded('Pod_Closed_lower_shell',(0,0,19.15),(70,45,18.3),8,pc,pod_mat,bottom=3,top=.15)
cavity = rounded('Tool_inner_cavity',(0,0,27),(65.6,40.6,29.6),6,pc,None,bottom=1.8,top=.1)
subtract(body,cavity)
lid = rounded('Pod_Closed_spring_lid',(0,0,30.25),(70,45,3.5),8,pc,pod_mat,bottom=.15,top=2.5)
channel = rounded('Tool_recessed_handle_channel',(3,0,34.7),(45,19.8,11),5,pc,None,bottom=.7,top=.1)
subtract(lid,channel)
lid['hinge_axis'] = 'Y at X=-30, Z=28.4'
box('Pod_Closed_latch_dust_cover',(18.5,1,25.8),(29,36,2),pc,pod_mat,.8)
body['closed_outer_dimensions_mm'] = [70,45,22]
body['corner_radius_mm'] = 8
led = cylinder('Pod_Closed_green_LED_3mm',(-22,12,31.7),(-22,12,32),1.5,pc,green)
for x in [-22,22]:
    rounded('Pod_Closed_hidden_saddle_clip_'+str(x),(x,0,9.9),(8,27,3.4),2,pc,pod_mat,bottom=.6,top=.6)
tab = rounded('Leash_Closed_manual_release_tab',(-40,0,24.1),(18,8,1),2,parts['Leash','Closed'],black,bottom=.4,top=.4)
tab['exposed_length_mm'] = 14

# The closed handle is a 40 mm flattened loop of 16 mm ribbon.
handle_points = []
for i in range(41):
    a = -math.pi/2+math.pi*i/40
    handle_points.append((21.4+1.35*math.cos(a),0,30.65+1.0*math.sin(a)))
for i in range(41):
    a = math.pi/2+math.pi*i/40
    handle_points.append((-15.9+1.35*math.cos(a),0,30.65+1.0*math.sin(a)))
handle = ribbon('Leash_Closed_orange_handle_loop_16mm',handle_points,16,parts['Leash','Closed'],orange,thickness=.45,cyclic=True)
handle['visible_length_mm'] = 40

lc = parts['Latch','Closed']
# Parallel cheeks constrain the cam slider to the long axis.
box('Latch_Closed_mounting_cradle',(21,-6,15),(23,17,2.4),lc,inner_mat,.7)
for y in [-13,-3]:
    box('Latch_Closed_axial_guide_'+str(y),(22,y,18.3),(19,1.3,5),lc,dark_metal,.3)
cam = mesh('Latch_Closed_axial_ramp_cam',[(13,-11.8,17),(29,-11.8,17),(29,-11.8,20),(13,-11.8,24),(13,-4.2,17),(29,-4.2,17),(29,-4.2,20),(13,-4.2,24)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],lc,steel)
bevel(cam,.35,4)
smooth(cam)
cam['travel_axis'] = '+X; guide cheeks constrain lateral movement'
cylinder('Latch_Closed_cam_follower',(23,-12.3,22),(23,-3.7,22),1.3,lc,steel)
cylinder('Latch_Closed_sear_lift_stem',(23,-8,22.5),(23,-8,28.6),1.1,lc,steel)
cylinder('Latch_Closed_sear_retaining_pin',(23,-8,28.6),(23,7.5,28.6),1.05,lc,steel)
box('Latch_Closed_handle_catch',(20,0,28.1),(5,5,3),lc,dark_metal,.5)
cylinder('Latch_Closed_solenoid_body',(8,11,16.5),(8,11,24.5),3.5,lc,dark_metal)
cylinder('Latch_Closed_solenoid_copper_band',(8,11,18.7),(8,11,21.8),3.57,lc,copper)
cylinder('Latch_Closed_solenoid_lifting_plunger',(8,11,24.5),(8,11,27.1),1.15,lc,steel)
box('Latch_Closed_shared_sear_lift_bridge',(15.5,9.6,27.8),(17,4,1.2),lc,steel,.3)
cylinder('Latch_Closed_sear_bridge_end',(23,8,27.8),(23,8,29.7),1.2,lc,steel)
cylinder('Latch_Closed_lid_hinge_axle',(-30,-15,28.3),(-30,15,28.3),.85,lc,steel)
spring_points = [(-30+1.8*math.cos(i*math.pi*14/180),-5+10*i/180,28.3+1.8*math.sin(i*math.pi*14/180)) for i in range(181)]
tube('Latch_Closed_lid_torsion_spring',spring_points,.27,lc,steel)
tube('Latch_Closed_spring_leg_body',[(-30,-5,30.1),(-27,-6,21)],.27,lc,steel)
tube('Latch_Closed_spring_leg_lid',[(-30,5,30.1),(-25,6,30.2)],.27,lc,steel)
tube('Latch_Closed_manual_release_link',[(-34,0,24.1),(-27,-14,22),(-2,-14,22),(14,-8,22)],.5,lc,dark_metal)

# Five straight runs and four rounded returns total about 150 mm.
fold_points = []
for level in range(5):
    z = 13.5+level*2.6
    left, right = -24, 2
    start, end = (left,right) if level%2 == 0 else (right,left)
    fold_points.extend([(start,0,z),(end,0,z)])
    if level < 4:
        for i in range(1,21):
            a = math.pi*i/20
            fold_points.append((end+(1 if level%2==0 else -1)*1.3*math.sin(a),0,z+1.3*(1-math.cos(a))))
fold = ribbon('Leash_Closed_accordion_stack_150mm',fold_points,20,parts['Leash','Closed'],grey,thickness=.7)
fold['modeled_length_mm'] = round(sum((Vector(a)-Vector(b)).length for a,b in zip(fold_points,fold_points[1:])),1)
ribbon('Leash_Closed_handle_join',[(-24,0,23.9),(-24.5,0,26),(-23,0,28),(-18,0,29.5)],16,parts['Leash','Closed'],orange)
ribbon('Leash_Closed_attached_leash_tail',[(2,0,13.5),(12,0,12.8),(27,0,12.7),(34,0,12),(39,0,11)],20,parts['Leash','Closed'],grey,thickness=.7)
hook_points = [(40+4.7*math.cos(t),3.7*math.sin(t),11.8) for t in [math.radians(-55+290*i/64) for i in range(65)]]
tube('Leash_Closed_harness_snap_hook',hook_points,.95,parts['Leash','Closed'],steel)
cylinder('Leash_Closed_snap_gate',(42.7,-3,11.8),(42.7,3,11.8),.6,parts['Leash','Closed'],steel)

for state in ['Cutaway','Released']:
    for group in ['Pod','Latch','Leash']:
        for obj in list(parts[group,'Closed'].objects):
            copy_to(obj,state,group)

# The section removes the near wall and near lid without exposing other states.
cut_body = bpy.data.objects['Pod_Cutaway_lower_shell']
cut_tool = box('Tool_near_shell_section',(0,-22,35),(90,39,40),parts['Pod','Cutaway'],None,0)
subtract(cut_body,cut_tool)
cut_lid = bpy.data.objects['Pod_Cutaway_spring_lid']
cut_tool = box('Tool_near_lid_section',(0,-13,35),(90,51,20),parts['Pod','Cutaway'],None,0)
subtract(cut_lid,cut_tool)
# Show the rear half of the loop so it does not mask the latch beneath it.
cut_handle = bpy.data.objects['Leash_Cutaway_orange_handle_loop_16mm']
for mod in list(cut_handle.modifiers):
    apply_modifier(cut_handle,mod)
cut_tool = box('Tool_handle_section',(0,-10,33),(70,20,10),parts['Leash','Cutaway'],None,0)
subtract(cut_handle,cut_tool)
bpy.data.objects.remove(bpy.data.objects['Pod_Cutaway_latch_dust_cover'],do_unlink=True)

# The lid and LED rotate together around the rear hinge.
pivot = Vector((-30,0,28.3))
lid_open = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(-104),4,'Y') @ Matrix.Translation(-pivot)
transform_geometry(bpy.data.objects['Pod_Released_spring_lid'],lid_open)
led_open = bpy.data.objects['Pod_Released_green_LED_3mm']
led_open.matrix_world = lid_open @ led_open.matrix_world
for name in ['orange_handle_loop_16mm','handle_join','accordion_stack_150mm','attached_leash_tail']:
    bpy.data.objects.remove(bpy.data.objects['Leash_Released_'+name],do_unlink=True)

rc = parts['Leash','Released']
spill_points = [(39,0,11),(32,0,15),(21,0,15),(10,-3,18),(3,-11,30),(1,-21,31),(7,-31,30),(17,-40,16),(25,-45,3),(37,-44,1.1),(49,-38,1),(61,-35,1),(70,-38,1.2)]
ribbon('Leash_Released_spilled_webbing_20mm',soften_path(spill_points),20,rc,grey,thickness=.7)
free_loop_points = []
for i in range(97):
    t = 2*math.pi*i/96
    free_loop_points.append((89+20*math.cos(t),-38,6.5+5.2*math.sin(t)))
ribbon('Leash_Released_free_orange_handle_16mm',free_loop_points,16,rc,orange,thickness=.5,cyclic=True)
ribbon('Leash_Released_handle_join',[(67,-38,1.1),(71,-38,1.5),(73,-38,2.4)],16,rc,orange)
for obj in parts['Latch','Released'].objects:
    if any(word in obj.name for word in ['sear_lift_stem','sear_retaining_pin','cam_follower','shared_sear_lift_bridge','sear_bridge_end']):
        obj.location.z += 2.8
    if 'axial_ramp_cam' in obj.name:
        obj.location.x += 3

# The ground lives with the studio lighting, leaving the requested six roots.
rounded('Studio_ground',(0,0,-1),(1600,1600,1.4),12,groups['Lights'],ground_mat,bottom=.2,top=.2)
def area_light(name, position, target, power, size, rgb):
    data = bpy.data.lights.new(name,'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    data.color = rgb
    obj = bpy.data.objects.new(name,data)
    groups['Lights'].objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj
area_light('Light_soft_key',(-35,-85,145),(0,0,15),650000,105,(1,.94,.88))
area_light('Light_soft_fill',(95,-15,85),(0,0,15),220000,110,(.88,.93,1))
area_light('Light_weak_rim',(-35,80,110),(0,0,20),310000,85,(1,1,1))

world = bpy.data.worlds.new('World_neutral_studio')
world.use_nodes = True
world.node_tree.nodes.get('Background').inputs[0].default_value = (.25,.25,.25,1)
world.node_tree.nodes.get('Background').inputs[1].default_value = .35

def camera(name, loc, target, scale):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name,data)
    groups['Cameras'].objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    data.type = 'ORTHO'
    data.ortho_scale = scale
    data.lens = 65
    data.clip_start = .1
    data.clip_end = 3000
    data.passepartout_alpha = 1
    return obj

cameras = {
    'Closed': camera('CAM_hero',(105,-130,125),(0,0,14),137),
    'Cutaway': camera('CAM_cutaway',(92,-142,137),(0,0,19),140),
    'Released': camera('CAM_released',(135,-170,154),(25,-9,41),230),
}

for index,state in enumerate(states):
    sc = scene if index == 0 else bpy.data.scenes.new(f'{index+1:02d}_{state}')
    if index:
        for group in groups.values():
            sc.collection.children.link(group)
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = .001
    sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.world = world
    sc.camera = cameras[state]
    sc.render.engine = 'BLENDER_EEVEE'
    sc.eevee.taa_samples = 128
    sc.eevee.taa_render_samples = 128
    sc.eevee.shadow_ray_count = 4
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 1200
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = -1.3
    sc.render.filepath = str(OUT / (cameras[state].name+'.png'))
    sc['state'] = state
    sc['purpose'] = 'Static product concept. Dimensions in millimeters.'
    bpy.context.window.scene = sc
    bpy.context.view_layer.update()
    layer = sc.view_layers[0]
    layer.name = state
    for group in ['Pod','Latch','Leash']:
        for child in layer.layer_collection.children[group].children:
            child.exclude = child.name != group+'_'+state
    if state == 'Released':
        layer.layer_collection.children['Latch'].exclude = True

bpy.context.window.scene = scene
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.clip_start = .1
            space.clip_end = 3000
            space.overlay.show_overlays = False
            space.show_gizmo = False
            space.shading.type = 'MATERIAL'
            space.shading.use_scene_lights = True
            space.shading.use_scene_world = True
            space.region_3d.view_perspective = 'CAMERA'
            space.region_3d.view_camera_zoom = 8

bpy.ops.object.select_all(action='DESELECT')
scene.tool_settings.use_keyframe_insert_auto = False
bpy.context.view_layer.update()
shell_points = [obj.matrix_world @ Vector(p) for obj in [body,lid] for p in obj.bound_box]
measured_shell = [round(max(p[i] for p in shell_points)-min(p[i] for p in shell_points),4) for i in range(3)]
validation = {
    'units': '1 Blender unit = 1 mm',
    'closed_shell_bounds_mm': measured_shell,
    'folded_webbing_length_mm': fold['modeled_length_mm'],
    'scenes': {sc.name:sc.camera.name for sc in bpy.data.scenes},
    'root_collections': [c.name for c in scene.collection.children],
    'objects': len(bpy.data.objects),
    'unnamed_objects': [o.name for o in bpy.data.objects if o.name.startswith(('Cube','Cylinder','Curve','Plane','Sphere'))],
}
(OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'wearable-leash-pod.blend'))
print('POD_BUILD_COMPLETE '+json.dumps(validation))
