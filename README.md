This is a basic implementation of a coding agent with a sandboxed environment and an orchestration layer, as per the assignment description.

## Architecture

- **Orchestrator**: A FastAPI server that manages agent jobs. It exposes endpoints to schedule tasks and check their status.
- **Agent**: A Python script that uses an LLM (GPT-4) to execute tasks. It runs inside a Docker container.
- **Agent Container**: A Docker image containing a sandboxed environment with tools like a shell, file system access, and development utilities. It includes a VNC server for live observation.
- **Workspace**: Each job gets a dedicated workspace directory, which is mounted into the agent container. This workspace is archived for download upon task completion.

## How to Run

### Prerequisites
- Docker
- Python 3.8+
- `uv` package manager (`pip install uv`)
- An OpenAI API key with access to GPT-4 models.

### 1. Setup
- **Install Dependencies**:
  ```bash
  uv sync
  ```
- **Set OpenAI API Key**: The orchestrator needs access to your OpenAI API key. You can set it as an environment variable:
  ```bash
  export OPENAI_API_KEY="your-key-here"
  ```

### 2. Build the Agent Container
Build the Docker image for the agent:
```bash
docker build -t agent-base:latest -f docker/Dockerfile .
```

### 3. Run the Orchestrator
Start the FastAPI server:
```bash
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000
```
Remember to have your `OPENAI_API_KEY` environment variable set in the terminal where you run this command.

### 4. Schedule a Task
Use `curl` or any API client to send a task to the agent.

**Example Task**: Create a file named `hello.txt` with "hello world" as its content.
```bash
curl -X POST http://localhost:8000/schedule \
-H "Content-Type: application/json" \
-d '{
    "prompt": "Create a file named hello.txt and put the text `hello world` inside it."
}'
```

This will return a `job_id` and a `vnc_port`.

### 5. View the Agent Live
You can watch the agent work in real-time.
1. The `/schedule` endpoint returns a `vnc_port`.
2. Open your web browser and navigate to `http://localhost:<vnc_port>`. For example, `http://localhost:6080`.
3. The VNC password is `agent`.

### 6. Check Job Status
Once the agent finishes (or you think it's done), you can check its status.
```bash
# Replace {job_id} with the ID you received from the schedule step
curl http://localhost:8000/status/{job_id}
```

If the `status` is `exited`, the response will contain a `download_url` for an archive of the agent's workspace.

## Design Choices & Next Steps
- **Sandboxing**: Docker provides a good level of isolation. For stronger security, Firecracker VMs would be the next step.
- **Scalability**: The current VNC port allocation is not scalable. A production system would need a dynamic port manager or a different way to expose the VNC service (e.g., through a proxy with path-based routing). The in-memory job store is also a bottleneck; a persistent database like Redis or PostgreSQL would be needed.
- **Context Management**: The agent currently sends the full conversation history. For very long tasks, a summarization or sliding window strategy would be necessary to manage the LLM's context window.
- **Reliability**: The orchestrator is a single point of failure. A more robust setup would involve multiple orchestrator instances and a persistent, shared job queue.
