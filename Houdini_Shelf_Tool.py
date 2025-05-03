# -----------------------------------------------------------------------------
# Houdini Shelf Tool: Generate 3D Mesh from Image via Local REST API
# -----------------------------------------------------------------------------
import hou
import requests
import os

# 1) Ask user to pick an input image
start_dir = hou.expandString("$HIP")
image_path = hou.ui.selectFile(
    start_directory=start_dir,
    title="Select Input Image",
    pattern="*.png,*.jpg,*.jpeg,*.tga,*.bmp",
    collapse_sequences=False,
    file_type=hou.fileType.Any
)
if not image_path:
    hou.ui.displayMessage("No image selected. Operation canceled.")
    raise hou.Error("User canceled file selection")

# 2) Define your API endpoint and parameters
url = "http://localhost:8000/generate_3d"
params = {
    "seed": -1,
    "ss_guidance_strength": 3.0,
    "ss_sampling_steps": 50,
    "slat_guidance_strength": 3.0,
    "slat_sampling_steps": 6
}

# 3) POST the image and parameters
hou.ui.setStatusMessage("Uploading image and generating 3D mesh…", severity=hou.severityType.Message)
try:
    with open(image_path, "rb") as img_file:
        files = {"image": img_file}
        response = requests.post(url, files=files, data=params)
except Exception as e:
    hou.ui.displayMessage(f"Network error:\n{e}")
    raise

# 4) Handle the response
if response.status_code != 200:
    hou.ui.displayMessage(f"Error {response.status_code}:\n{response.text}")
    raise hou.Error(f"Server returned {response.status_code}")

# 5) Save the .glb locally next to the image (or customize path here)
base, _ = os.path.splitext(image_path)
output_file = base + "_generated.glb"
with open(output_file, "wb") as out_f:
    out_f.write(response.content)

hou.ui.displayMessage(f"Mesh saved to:\n{output_file}", buttons=("OK",))

# 6) Import the generated .glb using a glTF Hierarchy node
obj = hou.node("/obj")
if not obj:
    raise hou.Error("Cannot find /obj context")

# Optional: clean up any previous import node
old = obj.node("gltf_import")
if old:
    old.destroy()

# Create the glTF Hierarchy HDA
gltf_node = obj.createNode("gltf_hierarchy", node_name="gltf_import")

# Set its file path to our newly generated .glb
gltf_node.parm("filename").set(output_file)

# Click the "Build Scene" button to actually import the hierarchy
# (the parm name may vary; if this fails, check the HDA's parameter interface)
gltf_node.parm("buildscene").pressButton()

# tidy up the network layout
obj.layoutChildren()

hou.ui.setStatusMessage("3D mesh built in /obj/gltf_import", severity=hou.severityType.ImportantMessage)
