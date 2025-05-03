# -----------------------------------------------------------------------------
# Python SOP – Generate 3‑D mesh from image via local REST API
# -----------------------------------------------------------------------------
import os
import requests
import hou

# Current node (the Python SOP) and its geometry
node = hou.pwd()
geo  = node.geometry()          # We don’t actually modify SOP geometry.

# -------------------------------------------------------------------------
# 1) Read parameters from the node
# -------------------------------------------------------------------------
def parm(name, default=None):
    try:
        return node.evalParm(name)
    except hou.OperationFailed:
        return default

image_path             = parm("image_path", "").strip()
seed                   = parm("seed", -1)
ss_guidance_strength   = parm("ss_guidance_strength", 3.0)
ss_sampling_steps      = parm("ss_sampling_steps", 50)
slat_guidance_strength = parm("slat_guidance_strength", 3.0)
slat_sampling_steps    = parm("slat_sampling_steps", 6)
make_gltf              = bool(parm("make_gltf_import", 1))

if not image_path:
    raise hou.NodeError("Please set ‘image_path’ on this Python SOP.")

if not os.path.isfile(image_path):
    raise hou.NodeError(f"Image not found:\n{image_path}")

# -------------------------------------------------------------------------
# 2) Call your local REST endpoint
# -------------------------------------------------------------------------
url    = "http://localhost:8000/generate_3d"
params = {
    "seed"                  : seed,
    "ss_guidance_strength"  : ss_guidance_strength,
    "ss_sampling_steps"     : ss_sampling_steps,
    "slat_guidance_strength": slat_guidance_strength,
    "slat_sampling_steps"   : slat_sampling_steps,
}

hou.setStatusMessage("Uploading image and generating 3‑D mesh…")

try:
    with open(image_path, "rb") as img:
        files = {"image": img}
        response = requests.post(url, files=files, data=params, timeout=600)
except Exception as err:
    raise hou.NodeError(f"Network error:\n{err}")

if response.status_code != 200:
    raise hou.NodeError(f"API returned {response.status_code}:\n{response.text}")

# -------------------------------------------------------------------------
# 3) Save the returned .glb next to the source image
# -------------------------------------------------------------------------
base, _      = os.path.splitext(image_path)
output_file  = f"{base}_generated.glb"

with open(output_file, "wb") as out_f:
    out_f.write(response.content)

hou.setStatusMessage(f"Mesh written to:\n{output_file}")

# -------------------------------------------------------------------------
# 4) OPTIONAL – build /obj/gltf_import so the user sees the mesh straight away
# -------------------------------------------------------------------------
if make_gltf:
    obj = hou.node("/obj")
    if obj is None:
        hou.ui.displayMessage("Cannot find /obj context ­– skipping import.")
    else:
        # Remove any previous import node created by this SOP
        existing = obj.node("gltf_import")
        if existing:
            existing.destroy()

        gltf_node = obj.createNode("gltf_hierarchy", "gltf_import")
        gltf_node.parm("filename").set(output_file)
        try:
            gltf_node.parm("buildscene").pressButton()
        except hou.OperationFailed:
            # Parameter name might differ on custom HDAs – ignore.
            pass

        obj.layoutChildren()
        hou.setStatusMessage("3‑D mesh built in /obj/gltf_import",
                             severity=hou.severityType.ImportantMessage)

