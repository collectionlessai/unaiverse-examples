import os
import re
import sys
import glob
import threading
import subprocess

# configuration
world_file_runner = "run_w.py"
agent_file_runners = "run_*.py"  # where * must be a number
log_to_file = True

# keep track of all running processes
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

    # if the process failed, signal to stop others
    if my_proc.returncode != 0:
        print(f"[{script_name}] ERROR: Exited with code {my_proc.returncode}")
        stop_event.set()
        terminate_all_processes()

    if log_file:
        log_file.close()


def terminate_all_processes():
    """Terminate all running processes."""
    for p in running_processes:
        if p.poll() is None:  # still running
            try:
                p.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # collect scripts
    scripts = [os.path.join(script_dir, world_file_runner)]
    pattern = re.compile(r".*\d+\.\w+$")
    for filename in sorted(glob.glob(os.path.join(script_dir, agent_file_runners))):
        base = os.path.basename(filename)
        if base == world_file_runner:
            continue
        if pattern.match(filename):
            scripts.append(filename)

    threads = []

    # clear addresses.txt
    if os.path.exists(os.path.join(script_dir, "addresses.txt")):
        os.remove(os.path.join(script_dir, "addresses.txt"))

    for i, script in enumerate(scripts):
        if stop_event.is_set():
            break

        if log_to_file:
            os.makedirs(os.path.join(script_dir, "log"), exist_ok=True)
            log_path = os.path.join(script_dir, "log", f"{os.path.basename(script)}.log")
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

    # wait for all threads to finish
    for t in threads:
        t.join()
