import torch
import torchvision
from unaiverse.agent import Agent
from unaiverse.custom import Custom
from unaiverse.streams import StreamType
from unaiverse.networking.node.node import Node
from unaiverse.modules.cnu.layers import LinearCNU
from unaiverse.modules.utils import transforms_factory, set_seed


class LightCNUNetwork(torch.nn.Module):
    """This is a simple CNN with a head layer composed of Continual Neural Units
    (CNUs, see https://doi.org/10.1007/978-3-031-70344-7_20)."""

    def __init__(self):
        super().__init__()

        # Backbone (ResNet50)
        self.network = torchvision.models.resnet50(weights="IMAGENET1K_V2")

        # Class names
        self.known_classes = 0
        self.max_classes = 10  # Upper bound
        self.class_names = ["unknown"] * self.max_classes

        # Freezing backbone
        for p in self.network.parameters():
            p.requires_grad = False
        self.network.eval()  # Keep BatchNorm off as well

        # Removing the original head and adding a new one
        in_features = self.network.fc.in_features  # 2048
        self.network.fc = LinearCNU(in_features, self.max_classes, key_mem_units=3, delta=1, beta_k=0.1)

    def forward(self, x: torch.Tensor):
        """The forward pass of the network."""
        return self.network(x)

    def get_class_ids(self, class_names: str | list[str]) -> torch.Tensor:
        """Get the class ids for the given class names (i.e., from class name to cross entropy class indices)."""
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
        """Get the class names given a set of prediction scores (logits)."""
        if x.ndim == 1:
            x = x.unsqueeze(0)  # Fully flat: treat as batch of size 1
        ids = torch.argmax(x, dim=1).tolist()
        return ", ".join(self.class_names[int(i)] for i in ids)


if __name__ == "__main__":
    set_seed(67)

    # Setting up debug-like env variables for local testing
    Custom.SKIP_WAS_ALIVE_CHECK = True
    Custom.ENV_IS_ISOLATED = True
    Custom.ENV_IS_PUBLIC = True

    # Network
    net = LightCNUNetwork()

    # Agent
    agent = Agent(proc=net,
                  proc_inputs=[StreamType(data_type="img",
                                          stream_to_proc_transforms=transforms_factory("rgb224"))],
                  proc_outputs=[StreamType(data_type="text",
                                           stream_to_proc_transforms=net.get_class_ids,
                                           proc_to_stream_transforms=net.get_class_names)],
                  proc_opts={'optimizer': torch.optim.SGD(net.parameters(), lr=0.5),
                             'losses': [torch.nn.functional.cross_entropy]})

    # Node hosting the student agent
    node = Node(node_name="CoLLAsStudent1_", hosted=agent, hidden=True, clock_delta=1./50.)

    # Running node
    node.run(join_world="CoLLAsTutorial_")
