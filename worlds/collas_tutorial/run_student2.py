import torch
from unaiverse.agent import Agent
from run_student1 import LightCNUNetwork
from unaiverse.streams import StreamType
from unaiverse.networking.node.node import Node
from unaiverse.modules.utils import transforms_factory

if __name__ == "__main__":

    # Network
    net = LightCNUNetwork()

    # Agent
    agent = Agent(proc=net,
                  proc_inputs=[StreamType(data_type="img",
                                          stream_to_proc_transforms=transforms_factory("rgb224"))],
                  proc_outputs=[StreamType(data_type="text",
                                           stream_to_proc_transforms=net.get_class_ids,
                                           proc_to_stream_transforms=net.get_class_names)],
                  proc_opts={'optimizer': torch.optim.SGD(net.parameters(), lr=0.05),
                             'losses': [torch.nn.functional.cross_entropy]})

    # Node hosting the student agent
    node = Node(node_name="CoLLAsStudent2", hosted=agent, hidden=True, clock_delta=1./50.)

    # Running node
    node.run(join_world="CoLLAsTutorial")
