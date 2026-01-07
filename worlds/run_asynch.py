import os
import re
import sys
import glob
import time
import shutil
import argparse
import threading
import subprocess

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
    parser = argparse.ArgumentParser(description="Run the world script.")
    parser.add_argument("world_name", help="Name of the world to run")
    parser.add_argument("-l", "--log", action="store_true", help="Activate logging")
    parser.add_argument("--max_run", type=int, default=-1,
                        help="Max number of runner to execute (default: no-limits)")

    args = parser.parse_args()

    # Access your variables like this:
    world_name = args.world_name
    log_to_file = args.log
    max_run = args.max_run

    main_dir = os.path.dirname(os.path.abspath(__file__))
    script_dir = str(os.path.join(main_dir, world_name))

    # Collect scripts
    scripts = [os.path.join(script_dir, world_file_runner)]
    pattern = re.compile(r".*\d+\.\w+$")
    for filename in sorted(glob.glob(os.path.join(script_dir, agent_file_runners))):
        base = os.path.basename(filename)
        if base == world_file_runner:
            continue
        if pattern.match(filename):
            scripts.append(filename)
        if 0 < max_run <= len(scripts):
            break

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
            [sys.executable, "-u", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            bufsize=1
        )
        running_processes.append(proc)

        t = threading.Thread(target=stream_output, args=(proc, os.path.basename(script), log_f))
        t.start()
        if i == 0:
            time.sleep(10.)  # Running world, wait a bit for role/node creation (or the other agents will not find it)
        threads.append(t)

    # Wait for all threads to finish
    for t in threads:
        t.join()
