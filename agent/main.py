import os
import time

def main():
    """
    The main entrypoint for the agent running inside the container.
    """
    task = os.environ.get("AGENT_TASK")
    if not task:
        print("AGENT_TASK environment variable not set. Exiting.")
        return

    # Log the task to a file in the workspace
    with open("task.log", "w") as f:
        f.write(f"Received task: {task}\n")

    # Simulate doing work
    print(f"Starting task: {task}")
    time.sleep(10) 
    print("Task finished.")

    with open("task.log", "a") as f:
        f.write("Task completed.\n")

if __name__ == "__main__":
    main() 