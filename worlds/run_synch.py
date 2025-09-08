import os
import re
import sys
import glob

# Configuration
world_file_runner = "run_w.py"
agent_file_runners = "run_*.py"
files_to_skip = {"run_synch.py", "run_asynch.py", "run_demo.py", "run_demo_a.py", "run_demo_b.py"}

initial_code = """
import os
import sys
from unaiverse.utils.server import Server
from unaiverse.networking.node.node import NodeSynchronizer

# Synchronizing nodes (for visualization purposes)
node_synchronizer = NodeSynchronizer()
"""

code_after_world = """
# Get world addresses
node_addresses = node.get_public_addresses()
node_synchronizer.add_node(node)
"""

code_after_every_agent = """
# Tell agent to join the world
node.ask_to_join_world(addresses=node_addresses)
node_synchronizer.add_node(node)
"""

final_code = """
# Running
node_synchronizer.run()
"""
methods_to_skip = {"run", "ask_to_join_world", "save_node_addresses_to_file"}  # Method calls to skip


def build_script(code_dir: str) -> str:

    def is_import(_line: str) -> bool:
        return (_line.strip().startswith("import ") or _line.strip().startswith("from ") or
                _line.strip().startswith("sys.path.append"))

    def contains_something_to_skip(_line: str, _methods: set[str]) -> bool:
        for _method in _methods:
            if re.search(rf"\b{re.escape(_method)}\s*\(", _line):
                return True
        return False

    imports = []
    unique_imports = set()
    code_lines = []

    # Initial code
    for line in initial_code.splitlines():
        if is_import(line):
            if line.strip() not in unique_imports:
                unique_imports.add(line.strip())
                imports.append(line.rstrip())
        else:
            if line.strip():
                code_lines.append(line.rstrip())

    # Fix path
    imports.append(f"sys.path.append('{os.path.join(code_dir)}')")

    # Collect world runner
    with open(os.path.join(code_dir, world_file_runner), "r") as f:
        skip_next = False
        for line in f:
            if skip_next:
                if line.strip().endswith(',') or line.strip().endswith('\\'):
                    skip_next = True
                else:
                    skip_next = False
                continue
            if contains_something_to_skip(line, methods_to_skip):
                if line.strip().endswith(',') or line.strip().endswith('\\'):
                    skip_next = True
                continue
            if is_import(line):
                if line.strip() not in unique_imports:
                    unique_imports.add(line.strip())
                    imports.append(line.strip())
            else:
                if line.strip():
                    code_lines.append(line.rstrip())

        # Add post-world code
        for line in code_after_world.splitlines():
            if line.strip():
                code_lines.append(line)

    # Collect agent runners
    for filename in sorted(glob.glob(os.path.join(code_dir, agent_file_runners))):
        if os.path.basename(filename) == world_file_runner:
            continue
        if os.path.basename(filename) in files_to_skip:
            continue
        with open(filename, "r") as f:
            skip_next = False
            for line in f:
                if skip_next:
                    if line.strip().endswith(',') or line.strip().endswith('\\'):
                        skip_next = True
                    else:
                        skip_next = False
                    continue
                if contains_something_to_skip(line, methods_to_skip):
                    if line.strip().endswith(',') or line.strip().endswith('\\'):
                        skip_next = True
                    continue
                if is_import(line):
                    if line.strip() not in unique_imports:
                        unique_imports.add(line.strip())
                        imports.append(line.strip())
                else:
                    if line.strip():
                        code_lines.append(line.rstrip())

            # Add post-agent code
            for line in code_after_every_agent.splitlines():
                if line.strip():
                    code_lines.append(line)

    # Final code
    for line in final_code.splitlines():
        if line.strip():
            code_lines.append(line)

    # Construct final script
    script = "\n".join(imports) + "\n\n" + "\n".join(code_lines) + "\n"
    return script


if __name__ == "__main__":
    if (len(sys.argv) != 2 and len(sys.argv) != 3) or \
            (len(sys.argv) == 3 and sys.argv[1] != "-s" and sys.argv[1] != "--server"):
        script_name = os.path.basename(sys.argv[0])
        print(f"Usage: python {script_name} [-s or --server] <world-name>")
        print(f"Flags: -s or --server: activate debug server (dev only)")
        sys.exit(1)

    if len(sys.argv) == 3:
        final_code = "Server(node_synchronizer=node_synchronizer)\n" + final_code
        world_name = sys.argv[2]
    else:
        world_name = sys.argv[1]

    main_dir = os.path.dirname(os.path.abspath(__file__))
    script_dir = os.path.join(main_dir, world_name)

    generated_script = build_script(script_dir)

    script_globals = {
        "__name__": "__generated_script.py__",
        "__file__": os.path.join(script_dir, "generated_script.py"),
        "__package__": None,
        "__builtins__": __builtins__,
    }

    os.chdir(script_dir)  # Working folder
    exec(generated_script, script_globals)
