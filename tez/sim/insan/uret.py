"""Build the human target for Gazebo: a MakeHuman (MPFB 2) person animated with CMU motion capture.

Runs inside Blender 4.5 with the MPFB 2 extension (uret.sh sets both up):

    blender -b --python uret.py -- --cikti <models/insan/meshes> --cmu <folder with the .bvh files>

Outputs walk.dae, run.dae, stand.dae (+ textures) and insan.json (hip heights, stride, natural speed). Every step was
checked with a side camera in Gazebo (2026-10-11, see KAYNAK.md):

- The motion is retargeted bone by bone (world rotation relative to the rest pose, both skeletons calibrated to the
  same bone directions) and the hip travel is scaled by the leg length ratio, so the planted foot does not slide.
- One gait cycle (left foot landing to left foot landing) is cut, turned to walk along +x and closed into a loop.
- COLLADA export needs keep_flat_curves (otherwise constant channels are dropped and bones snap to rest), and the
  file is cleaned for Gazebo: no armature object animation (Gazebo uses only the first animation of a file and then
  sees no x travel), flat channel list, joint ids equal to bone names.
"""

import json
import math
import os
import re
import sys

import bpy
from bl_ext.user_default.mpfb.services import ExportService, HumanService, LocationService, TargetService
from mathutils import Matrix, Quaternion, Vector

BVH_FPS = 120.0  # cgspeed conversion: Frame Time .0083333
OUT_FPS = 30
FLOOR_BAND = 0.02  # [m] a toe this close to its lowest height is on the ground
# Young adult man, 1.71 m, casual clothes (MakeHuman system assets, CC0)
MACRO = {"gender": 1.0, "age": 0.5, "muscle": 0.5, "weight": 0.5, "height": 0.62}
SKIN = "skins/young_caucasian_male/young_caucasian_male.mhmat"
ASSETS = [
    ("eyes/low-poly/low-poly.mhclo", "Eyes"),
    ("eyebrows/eyebrow001/eyebrow001.mhclo", "Eyebrows"),
    ("eyelashes/eyelashes01/eyelashes01.mhclo", "Eyelashes"),
    ("hair/short02/short02.mhclo", "Hair"),
    ("clothes/male_casualsuit03/male_casualsuit03.mhclo", "Clothes"),
    ("clothes/shoes02/shoes02.mhclo", "Clothes"),
]
RIG = "cmu_mb"  # same bone names as the CMU motion capture
# animation: (CMU clip, kind). Subject 35 walks and runs, 113 stands still.
CLIPS = {"walk": ("35_01.bvh", "cycle"), "run": ("35_17.bvh", "cycle"), "stand": ("113_21.bvh", "still")}
STAND_SECONDS = (1.0, 7.0)


def args() -> dict:
    a = sys.argv[sys.argv.index("--") + 1 :]
    return {a[i].lstrip("-"): a[i + 1] for i in range(0, len(a), 2)}


def build_human(blend: str) -> None:
    data = LocationService.get_user_data()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    macro = TargetService.get_default_macro_info_dict()
    macro.update(MACRO)
    human = HumanService.create_human(macro_detail_dict=macro)
    HumanService.set_character_skin(os.path.join(data, SKIN), human, skin_type="MAKESKIN")
    HumanService.add_builtin_rig(human, RIG)  # before the clothes, so they are rigged too
    for rel, kind in ASSETS:
        HumanService.add_mhclo_asset(os.path.join(data, rel), human, asset_type=kind, subdiv_levels=0)
    TargetService.bake_targets(human)
    ExportService.bake_modifiers_remove_helpers(human, bake_masks=True, bake_subdiv=False, remove_helpers=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)


def rig() -> bpy.types.Object:
    return next(o for o in bpy.data.objects if o.type == "ARMATURE")


def fk(tgt: bpy.types.Object, w: dict, hip: Vector) -> dict:
    """Armature-space matrices of all bones for world rotations w and the hip position (parents first)."""
    inv = tgt.matrix_world.inverted()
    mats = {}
    for bone in tgt.data.bones:
        if bone.parent is None:
            chain, loc = bone.matrix_local, inv @ hip
        else:
            chain = mats[bone.parent.name] @ bone.parent.matrix_local.inverted() @ bone.matrix_local
            loc = chain.translation
        mats[bone.name] = Matrix.Translation(loc) @ (inv.to_3x3() @ w[bone.name]).to_4x4() if bone.name in w else chain
    return mats


def local_basis(tgt: bpy.types.Object, w: dict, hip: Vector) -> dict:
    """pose_bone.matrix_basis (location, quaternion) of every bone."""
    mats = fk(tgt, w, hip)
    out = {}
    for bone in tgt.data.bones:
        parent = (
            mats[bone.parent.name] @ bone.parent.matrix_local.inverted() @ bone.matrix_local
            if bone.parent
            else bone.matrix_local
        )
        m = parent.inverted() @ mats[bone.name]
        out[bone.name] = (m.to_translation(), m.to_quaternion())
    return out


def retarget(tgt: bpy.types.Object, bvh: str) -> tuple[list, dict]:
    """CMU BVH -> per frame (world rotation of every target bone, hip position) and the target's toe tracks."""
    bpy.ops.import_anim.bvh(filepath=bvh, rotate_mode="NATIVE", axis_forward="-Z", axis_up="Y", use_fps_scale=False)
    src = bpy.context.selected_objects[0]
    f0, f1 = map(int, src.animation_data.action.frame_range)

    def world_rest(o: bpy.types.Object, b: str) -> Matrix:
        return o.matrix_world @ o.data.bones[b].matrix_local

    def leg(o: bpy.types.Object) -> float:
        return sum(o.data.bones[b].length * o.matrix_world.to_scale()[0] for b in ("LeftUpLeg", "LeftLeg"))

    ratio = leg(tgt) / leg(src)
    bones = [b.name for b in tgt.data.bones if b.name in src.data.bones]
    cal, rs_rest = {}, {}
    for b in bones:
        rt, rs = world_rest(tgt, b).to_3x3().normalized(), world_rest(src, b).to_3x3().normalized()
        # target rest frame turned so its bone points like the source rest bone (A-pose vs T-pose)
        cal[b] = (rt @ Vector((0, 1, 0))).rotation_difference(rs @ Vector((0, 1, 0))).to_matrix() @ rt
        rs_rest[b] = rs
    raw = []
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        rot = {b: (src.matrix_world @ src.pose.bones[b].matrix).to_3x3().normalized() for b in bones}
        hip = (src.matrix_world @ src.pose.bones["Hips"].matrix).translation.copy()
        toe = min((src.matrix_world @ src.pose.bones[s + "ToeBase"].matrix).translation.z for s in ("Left", "Right"))
        raw.append((rot, hip, toe))
    floor = sorted(t for *_, t in raw)[len(raw) // 20]
    hip0 = raw[0][1].copy()
    frames, toes = [], {"Left": [], "Right": []}
    for rot, hip, _ in raw:
        w = {b: rot[b] @ rs_rest[b].inverted() @ cal[b] for b in bones}
        # hip travel and height scaled by the leg ratio: the feet then step as far as the hips move
        p = Vector((ratio * (hip.x - hip0.x), ratio * (hip.y - hip0.y), ratio * (hip.z - floor)))
        frames.append((w, p))
        mats = fk(tgt, w, p)
        for s in toes:
            toes[s].append((tgt.matrix_world @ mats[s + "ToeBase"]).translation.copy())
    bpy.data.objects.remove(src)
    print(f"RETARGET {os.path.basename(bvh)}: {len(frames)} frames, leg ratio {ratio:.4f}")
    return frames, toes


def stances(track: list, floor: float) -> list[tuple[int, int]]:
    out, i = [], 0
    while i < len(track):
        if track[i].z < floor + FLOOR_BAND:
            j = i
            while j + 1 < len(track) and track[j + 1].z < floor + FLOOR_BAND:
                j += 1
            if j - i > 10:
                out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def cut(tgt: bpy.types.Object, frames: list, toes: dict, kind: str) -> tuple[list, dict]:
    """One loopable clip facing +x with the feet on the floor -> [(world rotations, hip)] and its numbers."""
    n = len(frames)
    if kind == "cycle":
        left = toes["Left"]
        st = stances(left, sorted(t.z for t in left)[n // 20])
        # a full cycle between two left-foot landings (skip the first, it may be partial)
        a, b = (st[1][0], st[2][0]) if len(st) > 2 else (st[0][0], st[1][0])
    else:
        a, b = int(STAND_SECONDS[0] * BVH_FPS), min(n - 1, int(STAND_SECONDS[1] * BVH_FPS))
    clip = frames[a : b + 1]
    if kind == "cycle":
        d = clip[-1][1] - clip[0][1]
    else:  # facing direction of the hips: forward = left x up
        m0 = fk(tgt, *clip[0])
        d = (m0["LeftUpLeg"].translation - m0["RightUpLeg"].translation).cross(Vector((0, 0, 1)))
    yaw = math.atan2(d.y, d.x)
    rot = Matrix.Rotation(-yaw, 3, "Z")
    start, drift = clip[0][1].copy(), rot @ (clip[-1][1] - clip[0][1])
    out = []
    for i, (w, hip) in enumerate(clip):
        f = i / (len(clip) - 1)
        p = rot @ (hip - start)
        p.z = hip.z
        # no sideways drift over a walking cycle; a standing clip ends where it started
        p -= f * (Vector((0, drift.y, 0)) if kind == "cycle" else Vector((drift.x, drift.y, 0)))
        out.append(({k: rot @ m for k, m in w.items()}, p))
    # feet on the floor: the lowest toe joint at its rest height
    rest_toe = min((tgt.matrix_world @ tgt.data.bones[s + "ToeBase"].matrix_local).translation.z for s in toes)
    lowest = min((fk(tgt, w, p)[s + "ToeBase"]).translation.z for w, p in out for s in toes)
    out = [(w, p + Vector((0, 0, rest_toe - lowest))) for w, p in out]
    travel = out[-1][1].x - out[0][1].x
    seconds = (b - a) / BVH_FPS
    info = {
        "sure_s": round(seconds, 3),
        "ilerleme_m": round(travel, 4),
        "dogal_hiz_mps": round(travel / seconds, 3),
        "kalca_yukseklik_m": round(sum(p.z for _, p in out) / len(out), 4),
    }
    return out, info


def bake(tgt: bpy.types.Object, clip: list, name: str) -> None:
    """Keyframes at OUT_FPS; the last pose blends into the first so the loop has no seam."""
    basis = [local_basis(tgt, w, p) for w, p in clip]
    first, last = basis[0], basis[-1]
    for bn in first:
        err = first[bn][1] @ last[bn][1].inverted()
        for i, fr in enumerate(basis):
            fr[bn] = (fr[bn][0], Quaternion().slerp(err, i / (len(basis) - 1)) @ fr[bn][1])
    step = round(BVH_FPS / OUT_FPS)
    keys = list(range(0, len(basis), step))
    if keys[-1] != len(basis) - 1:
        keys.append(len(basis) - 1)
    sc = bpy.context.scene
    sc.render.fps = OUT_FPS
    tgt.animation_data_create()
    tgt.animation_data.action = bpy.data.actions.new(name)
    for j, i in enumerate(keys):
        for bn, (loc, q) in basis[i].items():
            pb = tgt.pose.bones[bn]
            pb.rotation_mode = "QUATERNION"
            pb.location, pb.rotation_quaternion = loc, q
            pb.keyframe_insert("location", frame=j)
            pb.keyframe_insert("rotation_quaternion", frame=j)
    sc.frame_start, sc.frame_end = 0, len(keys) - 1


def simplify_materials() -> None:
    """Diffuse texture -> base colour (alpha for hair and lashes): what the COLLADA exporter can write."""
    for m in bpy.data.materials:
        nodes = m.node_tree.nodes if m.node_tree else []
        tex = next((n for n in nodes if n.type == "TEX_IMAGE" and n.name == "diffuseTexture" and n.image), None)
        if tex is None:
            continue
        img, nt = tex.image, m.node_tree
        nt.nodes.clear()
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if any(k in m.name for k in ("eyebrow", "eyelash", "short", "hair")):
            nt.links.new(t.outputs["Alpha"], bsdf.inputs["Alpha"])
            m.blend_method = "CLIP"
        bsdf.inputs["Roughness"].default_value = 0.8
        nt.links.new(bsdf.outputs["BSDF"], nt.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])


def export(tgt: bpy.types.Object, path: str) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.data.objects:
        if o == tgt or (o.type == "MESH" and o.parent == tgt):
            o.select_set(True)
    bpy.context.view_layer.objects.active = tgt
    bpy.ops.wm.collada_export(
        filepath=path,
        selected=True,
        include_children=True,
        include_armatures=True,
        deform_bones_only=True,
        include_animations=True,
        include_all_actions=False,
        export_animation_type_selection="sample",
        sampling_rate=1,
        keep_flat_curves=True,  # otherwise constant channels are dropped and those bones snap to rest
        keep_keyframes=True,
        triangulate=True,
        use_texture_copies=True,
        export_global_forward_selection="Y",
        export_global_up_selection="Z",
    )


def fix_for_gazebo(path: str, armature: str) -> None:
    s = open(path, encoding="utf-8").read()
    prefix = armature.replace(".", "_") + "_"
    # 1. the armature object's own (constant) animation: Gazebo would take it as the animation of the file
    s = re.sub(r'\s*<animation id="' + prefix + r'[a-z]+_transform"[^>]*>.*?</animation>', "", s, flags=re.S)
    # 2. no wrapper around the channels: one flat list is one animation for Gazebo's loader
    s = re.sub(r'<animation id="action_container-[^"]*"[^>]*>\s*', "", s, count=1)
    i = s.index("</library_animations>")
    j = s.rindex("</animation>", 0, i)
    s = s[:j] + s[j + len("</animation>") :]
    # 3. joint ids equal to the bone names
    bones = set(re.findall(r'<node id="' + prefix + r'([^"]+)" name="\1" sid="\1" type="JOINT"', s))
    pat = "|".join(sorted(map(re.escape, bones), key=len, reverse=True))
    s = re.sub(r'id="' + prefix + "(" + pat + r')"', r'id="\1"', s)
    s = re.sub(r"#" + prefix + "(" + pat + r")<", r"#\1<", s)
    s = re.sub(r'target="' + prefix + "(" + pat + r")/", r'target="\1/', s)
    open(path, "w", encoding="utf-8").write(s)


def main() -> None:
    a = args()
    out, cmu = a["cikti"], a["cmu"]
    os.makedirs(out, exist_ok=True)
    blend = os.path.join(out, "insan.blend")
    build_human(blend)
    meta = {"kaynak": "MakeHuman (MPFB 2, CC0) + CMU motion capture", "animasyonlar": {}}
    for name, (clip_file, kind) in CLIPS.items():
        bpy.ops.wm.open_mainfile(filepath=blend)
        tgt = rig()
        frames, toes = retarget(tgt, os.path.join(cmu, clip_file))
        clip, info = cut(tgt, frames, toes, kind)
        bake(tgt, clip, name)
        simplify_materials()
        path = os.path.join(out, f"{name}.dae")
        export(tgt, path)
        fix_for_gazebo(path, tgt.name)
        meta["animasyonlar"][name] = info | {"cmu": clip_file}
        print("ANIM", name, info)
    bpy.ops.wm.open_mainfile(filepath=blend)
    body = [o for o in bpy.data.objects if o.type == "MESH" and o.name == "Human"][0]
    zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
    meta["boy_m"] = round(max(zs) - min(zs), 3)
    with open(os.path.join(out, "insan.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    os.remove(blend)
    print("TAMAM", out, meta["boy_m"])


main()
