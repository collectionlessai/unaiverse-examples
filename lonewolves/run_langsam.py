import os
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import LangSegmentAnything
from unaiverse.utils.misc import save_node_addresses_to_file

"""
Based on Language Segment-Anything, https://github.com/luca-medeiros/lang-segment-anything

*** Requirements:
python >= 3.11 (right now it fails compiling with 3.13, better stay with 3.12),
expected torch==2.4.1 torchvision==0.19.1, and it will force these versions (torch and torchvision) by running the
command below (warning!)
Important: use transformers==4.44.2

*** Installation:
pip install -U git+https://github.com/luca-medeiros/lang-segment-anything.git

When running the model the first time, it will download the frozen-model-dependencies.
If the download of model.safetensors gets stuck or does not start at all, manually download it:

wget https://huggingface.co/IDEA-Research/grounding-dino-base/resolve/main/model.safetensors

Then copy model.safetensors to the cache folder, usually
~/.cache/huggingface/hub/models--IDEA-Research--grounding-dino-base
Look for the "snapshots" sub-folder and, inside of it, look for a folder like (it changes every time)
"12bdfa3120f3e7ec7b434d90674b3396eccf88eb", and place model.safetensors there!
Then run the model again to complete the other remaining downloads (if any... actually there shouldn't be any).

*** Run example (just as a reference):

    model = LangSAM()
    image_pil = Image.open("car.jpeg").convert("RGB")
    text_prompt = "wheel."
    results = model.predict([image_pil], [text_prompt])

*** Output
The variable "results" is a list with 1 element (in the running example above).
The variable "results[0]" is a dict with keys ['scores', 'labels', 'boxes', 'masks', 'mask_scores'].
results[0]['scores']: mono-dim numpy array with some float32 (4 in the running example), I guess the confidence on
    attaching a label to each segment that was found.
results[0]['labels']: list of strings, with the name of the label attached to each segment
    (['wheel', 'wheel', 'wheel', 'wheel'] in the running example).
results[0]['boxes']: 2-dim numpy array, with 4 columns (float32) and some rows (4 in the running example),
    I guess each row is a bounding box x,y,w,h of a segment.
results[0]['masks']: 3-dim numpy array, with some 2D binary masks (float32), one for each segment
    (shape=(4, 1500, 2250) in the running example).
results[0]['mask_scores']: mono-dim numpy array with some float32 (4 in the running example), I guess the confidence on
    each mask that was predicted.
"""

# Agent
agent = Agent(proc=LangSegmentAnything(),
              proc_inputs=[Data4Proc(data_type="img", pubsub=False, private_only=False),
                           Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="img", pubsub=False, private_only=False)],
              proc_opts={})

# TODO replace node_id="..." with node_name="Test0"
# TODO replace password with unaiverse key
# Node hosting agent
node_agent = Node(node_id="e4fc5f368f334df5bfb8d5bec501c776",
                  unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# Dumping public addresses to file
save_node_addresses_to_file(node_agent, os.path.dirname(__file__), public=True)

# Running node
node_agent.run()
