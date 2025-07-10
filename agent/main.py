import os
import openai
from dotenv import load_dotenv
import json
import subprocess

# --- Agent Tools ---

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
    
    system_prompt = get_tools_prompt()
    conversation_history = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"The user's task is: {task}"}
    ]

    while True:
        print("\n--- Thinking... ---")
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=conversation_history,  # type: ignore
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


    print("Agent finished task.")

if __name__ == "__main__":
    main() 