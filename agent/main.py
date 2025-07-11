import os
import openai
from dotenv import load_dotenv
import json
import subprocess
from jupyter_client.blocking.client import BlockingKernelClient

# --- Jupyter Kernel Manager ---

class JupyterKernelManager:
    _instance = None
    kc: BlockingKernelClient | None = None
    connection_file: str = "/home/agent/workspace/kernel.json"

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(JupyterKernelManager, cls).__new__(cls)
        return cls._instance

    def start_kernel(self):
        if self.kc is None:
            if os.path.exists(self.connection_file):
                print("Connecting to existing Jupyter kernel...")
                try:
                    kc = BlockingKernelClient()
                    kc.load_connection_file(self.connection_file)
                    kc.start_channels()
                    self.kc = kc
                    print("Connected to Jupyter kernel.")
                except Exception as e:
                    print(f"Failed to connect to Jupyter kernel: {e}")
            else:
                print("Jupyter kernel connection file not found. Code execution will not be available.")
    
    def execute(self, code):
        if not self.kc:
            return "Error: Jupyter kernel is not running."
        
        print(f"Executing code in Jupyter: \n---\n{code}\n---")
        self.kc.execute(code)
        
        output = ""
        while True:
            try:
                msg = self.kc.get_iopub_msg(timeout=3)
                msg_type = msg['header']['msg_type']

                if msg_type == 'status' and msg['content']['execution_state'] == 'idle':
                    # Idle status means execution is complete
                    break

                if msg_type == 'stream':
                    output += msg['content']['text']
                elif msg_type == 'execute_result':
                    output += msg['content']['data'].get('text/plain', '')
                elif msg_type == 'error':
                    output += "\n".join(msg['content']['traceback'])
                    break # Stop on error
            except Exception as e:
                # Timeout means no more messages
                break

        return f"Jupyter Output:\n{output}"

# Initialize the kernel manager
jupyter_manager = JupyterKernelManager()

# --- Agent Context Management ---

CONTEXT_FILE = "/home/agent/workspace/agent_context.json"
# Keep the system prompt, user task, and the last N messages to manage context window
MAX_HISTORY_MESSAGES = 20

def load_conversation_history():
    """Loads the conversation history from the context file if it exists."""
    if os.path.exists(CONTEXT_FILE):
        try:
            with open(CONTEXT_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading context file: {e}. Starting with a fresh history.")
            return []
    return []

def save_conversation_history(history):
    """Saves the conversation history to the context file."""
    try:
        with open(CONTEXT_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except IOError as e:
        print(f"Error saving context file: {e}")

def prune_conversation_history(history):
    """Prunes the history to stay within the approximate token limit."""
    if len(history) > MAX_HISTORY_MESSAGES:
        # Keep the first two messages (system prompt, user task) and the most recent ones.
        return history[:2] + history[-(MAX_HISTORY_MESSAGES - 2):]
    return history


# --- Agent Tools ---

def execute_xdot(command):
    """
    Executes an xdotool command for GUI control.
    NOTE: The DISPLAY environment variable must be set correctly in the container (e.g., DISPLAY=:1).
    Example commands: 'mousemove 100 200', 'click 1', 'key F5', 'type "hello world"'
    """
    try:
        full_command = f"xdotool {command}"
        print(f"Executing GUI command: {full_command}")
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True, check=True)
        return f"xdotool STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.CalledProcessError as e:
        return f"Error executing xdotool command: {e}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
    except FileNotFoundError:
        return "Error: xdotool command not found. Make sure it is installed and in the system's PATH."

def execute_python_code(code):
    """
    Executes a block of Python code in a stateful Jupyter kernel. 
    Variables and imports from previous executions are preserved.
    """
    return jupyter_manager.execute(code)

def list_files(path="."):
    """Lists files in a specified directory."""
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Error listing files: {e}"

def read_file(path):
    """Reads the content of a file."""
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(path, content):
    """Writes content to a file."""
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {path}."
    except Exception as e:
        return f"Error writing to file: {e}"

def execute_shell(command):
    """Executes a shell command."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"

def finish_task():
    """Signals that the task is finished."""
    return "TASK_FINISHED"

# --- Tool Dispatcher ---

tools = {
    "execute_xdot": execute_xdot,
    "execute_python_code": execute_python_code,
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "execute_shell": execute_shell,
    "finish_task": finish_task,
}

def get_tools_prompt():
    """Generates the tool descriptions for the LLM prompt."""
    prompt = "You are a coding agent. Your goal is to complete the user's task. You have the following tools available:\n\n"
    for name, func in tools.items():
        # A simple way to get parameter names. More robust inspection could be used.
        import inspect
        params = inspect.signature(func).parameters
        param_names = ", ".join(params.keys())
        prompt += f"- Tool: `{name}`\n"
        prompt += f"  - Description: {func.__doc__}\n"
        prompt += f"  - Arguments: `{param_names}`\n"

    prompt += """
You must respond with a JSON object that contains the key "tool_name" and "args".
The "args" must be a dictionary of arguments for the chosen tool.
If you believe the task is complete, use the `finish_task` tool.

Example:
{
    "tool_name": "list_files",
    "args": {
        "path": "."
    }
}
"""
    return prompt


def main():
    """
    The main entry point for the agent.
    """
    load_dotenv()

    # Start the Jupyter kernel client
    jupyter_manager.start_kernel()
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")
    
    client = openai.OpenAI(api_key=api_key)

    # Get the task for the agent
    task = os.getenv("AGENT_TASK")
    if not task:
        print("AGENT_TASK environment variable not set. Exiting.")
        return

    print(f"Received task: {task}")
    
    conversation_history = load_conversation_history()
    
    if not conversation_history:
        print("No previous context found. Starting a new conversation.")
        system_prompt = get_tools_prompt()
        conversation_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"The user's task is: {task}"}
        ]
    else:
        print(f"Loaded {len(conversation_history)} messages from previous context.")


    while True:
        print("\n--- Thinking... ---")

        # Prune the history before sending it to the model
        pruned_history = prune_conversation_history(conversation_history)

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=pruned_history,  # type: ignore
            response_format={"type": "json_object"},
        )
        
        assistant_message = response.choices[0].message
        conversation_history.append(assistant_message.model_dump(exclude_unset=True))

        if not assistant_message.content:
            print("Invalid response from LLM: No content.")
            conversation_history.append({
                "role": "system",
                "content": "Invalid response. Please respond with a valid JSON object. Your last response was empty."
            })
            continue

        try:
            tool_call = json.loads(assistant_message.content)
            tool_name = tool_call.get("tool_name")
            args = tool_call.get("args", {})

            print(f"Calling tool: {tool_name} with args: {args}")

            if tool_name in tools:
                tool_function = tools[tool_name]
                
                # Special case for finish_task
                if tool_function == finish_task:
                    print("Agent has decided to finish the task.")
                    break

                observation = tool_function(**args)
                print(f"Observation: {observation}")
                
                conversation_history.append({
                    "role": "system",
                    "content": f"Observation from tool {tool_name}:\n{observation}",
                })
            else:
                print(f"Unknown tool: {tool_name}")
                conversation_history.append({
                    "role": "system",
                    "content": f"Error: Tool '{tool_name}' not found.",
                })

        except json.JSONDecodeError:
            print(f"Invalid JSON response from LLM: {assistant_message.content}")
            # We could add this error to the history to allow for self-correction
            conversation_history.append({
                "role": "system",
                "content": f"Invalid JSON. Please respond with a valid JSON object. Response was: {assistant_message.content}"
            })
        
        # Save the full, un-pruned history after each cycle
        save_conversation_history(conversation_history)


    print("Agent finished task.")

if __name__ == "__main__":
    main() 