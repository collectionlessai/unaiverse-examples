import torch
import torchvision
from unaiverse.agent import Agent
from unaiverse.streams import StreamType
from unaiverse.networking.node.node import Node
from unaiverse.modules.cnu.layers import LinearCNU
from unaiverse.modules.utils import transforms_factory


class LightCNUNetwork(torch.nn.Module):
    def __init__(self):
        super().__init__()

        # Backbone
        self.network = torchvision.models.mobilenet_v3_small(weights="IMAGENET1K_V1")

        # Class names
        self.known_classes = 0
        self.max_classes = 10
        self.class_names = ["unknown"] * self.max_classes

        # Freezing backbone
        for p in self.network.parameters():
            p.requires_grad = False

        # Removing the original head (classifier) and adding a new CNU-based one
        in_features = self.network.classifier[0].in_features  # 576
        self.network.classifier = LinearCNU(in_features, self.max_classes, key_mem_units=10, delta=1)

    def forward(self, x: torch.Tensor):
        return self.network(x)

    def get_class_ids(self, class_names: str | list[str]) -> torch.Tensor:
        if isinstance(class_names, str):
            class_names = [class_names]
        ids = []
        for class_name in class_names:
            if class_name in self.class_names[0:self.known_classes]:
                ids.append(self.class_names.index(class_name, 0, self.known_classes))
            elif self.known_classes >= self.max_classes:
                ids.append(-100)  # This index is ignored by the torch implementation of the cross entropy
            else:
                ids.append(self.known_classes)
                self.class_names[self.known_classes] = class_name
                self.known_classes += 1
        return torch.tensor(ids, dtype=torch.long)

    def get_class_names(self, x: torch.Tensor) -> str:
        if x.ndim == 1:
            x = x.unsqueeze(0)  # Fully flat: treat as batch of size 1
        ids = torch.argmax(x, dim=1).tolist()
        return ", ".join(self.class_names[int(i)] for i in ids)


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
    node = Node(node_name="CoLLAsStudent1", hosted=agent, hidden=True, clock_delta=1./50.)

    # Running node
    node.run(join_world="CoLLAsTutorial")
