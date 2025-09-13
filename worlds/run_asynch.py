import os
import re
import sys
import glob
import shutil
import threading
import subprocess
import time

# Config
world_file_runner = "run_w.py"
agent_file_runners = "run_*.py"  # Where * must be a number

# Keep track of all running processes
running_processes = []
stop_event = threading.Event()


def stream_output(my_proc, _script_name, log_file=None):
    """Read process stdout line by line and print (and optionally log)."""
    for line in my_proc.stdout:
        sys.stdout.write(f"[{_script_name}] {line}")
        sys.stdout.flush()
        if log_file:
            log_file.write(line)
            log_file.flush()
    my_proc.wait()

    # If the process failed, signal to stop others
    if my_proc.returncode != 0:
        print(f"[{_script_name}] ERROR: Exited with code {my_proc.returncode}")
        stop_event.set()
        terminate_all_processes()

    if log_file:
        log_file.close()


def terminate_all_processes():
    """Terminate all running processes."""
    for p in running_processes:
        if p.poll() is None:  # Still running
            try:
                p.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    if (len(sys.argv) != 2 and len(sys.argv) != 3) or \
            (len(sys.argv) == 3 and sys.argv[1] != "-l" and sys.argv[1] != "--log"):
        script_name = os.path.basename(sys.argv[0])
        print(f"Usage: python {script_name} [-l or --log] <world-name>")
        print(f"Flags: -l or --log: activate logging ('log' folder inside the world folder)")
        sys.exit(1)

    if len(sys.argv) == 3:
        log_to_file = True
        world_name = sys.argv[2]
    else:
        log_to_file = False
        world_name = sys.argv[1]

    main_dir = os.path.dirname(os.path.abspath(__file__))
    script_dir = os.path.join(main_dir, world_name)

    # Collect scripts
    scripts = [os.path.join(script_dir, world_file_runner)]
    pattern = re.compile(r".*\d+\.\w+$")
    for filename in sorted(glob.glob(os.path.join(script_dir, agent_file_runners))):
        base = os.path.basename(filename)
        if base == world_file_runner:
            continue
        if pattern.match(filename):
            scripts.append(filename)

    threads = []

    # Clear addresses.txt
    if os.path.exists(os.path.join(script_dir, "addresses.txt")):
        os.remove(os.path.join(script_dir, "addresses.txt"))

    log_dir = os.path.join(script_dir, "log")
    if log_to_file:
        if os.path.exists(log_dir) and os.path.isdir(log_dir):
            shutil.rmtree(log_dir)
        os.makedirs(log_dir, exist_ok=True)

    os.chdir(script_dir)  # Working folder

    for i, script in enumerate(scripts):
        if stop_event.is_set():
            break

        if log_to_file:
            log_path = os.path.join(log_dir, f"{os.path.basename(script)}.log")
            log_f = open(log_path, "w+")
        else:
            log_f = None

        proc = subprocess.Popen(
            ["python3", "-u", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            bufsize=1
        )
        running_processes.append(proc)

        t = threading.Thread(target=stream_output, args=(proc, os.path.basename(script), log_f))
        t.start()
        if i == 0:
            time.sleep(10)  # Running world, wait a bit for role/node creation (or the other agents will not find it)
        threads.append(t)

    # Wait for all threads to finish
    for t in threads:
        t.join()
