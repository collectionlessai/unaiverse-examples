import os
import re
import sys
import glob
import shutil
import threading
import subprocess

# Config
world_file_runner = "run_w.py"
agent_file_runners = "run_*.py"  # Where * must be a number
log_to_file = True

# Keep track of all running processes
running_processes = []
stop_event = threading.Event()


def stream_output(my_proc, script_name, log_file=None):
    """Read process stdout line by line and print (and optionally log)."""
    for line in my_proc.stdout:
        sys.stdout.write(f"[{script_name}] {line}")
        sys.stdout.flush()
        if log_file:
            log_file.write(line)
            log_file.flush()
    my_proc.wait()

    # If the process failed, signal to stop others
    if my_proc.returncode != 0:
        print(f"[{script_name}] ERROR: Exited with code {my_proc.returncode}")
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
    if len(sys.argv) != 2:
        script_name = os.path.basename(sys.argv[0])
        print(f"Usage: python {script_name} <world-name>")
        sys.exit(1)

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

    for i, script in enumerate(scripts):
        if stop_event.is_set():
            break

        if log_to_file:
            log_dir = os.path.join(script_dir, "log")
            if os.path.exists(log_dir) and os.path.isdir(log_dir):
                shutil.rmtree(log_dir)
            os.makedirs(log_dir, exist_ok=True)
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
        threads.append(t)

    # Wait for all threads to finish
    for t in threads:
        t.join()
