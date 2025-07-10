import docker
from docker.errors import APIError, NotFound
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
import os
import shutil
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount the 'downloads' directory to serve static files
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

# Initialize Docker client
docker_client = docker.from_env()

# In-memory job store
jobs = {}

class Task(BaseModel):
    prompt: str

@app.post("/schedule")
async def schedule_task(task: Task):
    """
    Accepts a plain-text task and schedules it to run in a new agent container.
    """
    job_id = str(uuid.uuid4())
    
    # Create a workspace directory for the agent on the host
    workspace_dir = os.path.abspath(f"workspaces/{job_id}")
    os.makedirs(workspace_dir, exist_ok=True)

    # Get OpenAI API Key from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set on the server.")

    try:
        # We need to manage ports better for scaling. For now, a simple increment is fine.
        vnc_port = 6080 + len(jobs)
        container = docker_client.containers.run(
            "agent-base:latest",
            detach=True,
            name=f"agent-job-{job_id}",
            environment={
                "AGENT_TASK": task.prompt,
                "OPENAI_API_KEY": openai_api_key
            },
            volumes={
                workspace_dir: {"bind": "/home/agent/workspace", "mode": "rw"}
            },
            ports={'6080/tcp': vnc_port} 
        )
        jobs[job_id] = {
            "status": "running",
            "task": task.prompt,
            "container_id": container.id,
            "workspace": workspace_dir,
            "vnc_port": vnc_port
        }
    except APIError as e:
        raise HTTPException(status_code=500, detail=f"Failed to start agent container: {e}")

    return {"job_id": job_id, "vnc_port": vnc_port}

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Returns the status of a job.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        container = docker_client.containers.get(job["container_id"])
        job["status"] = container.status
    except NotFound:
        job["status"] = "exited"
    except APIError as e:
        raise HTTPException(status_code=500, detail=f"Failed to get container status: {e}")

    # If the job is finished, create a downloadable archive of the workspace
    if job["status"] == "exited" and "download_url" not in job:
        archive_name = f"{job_id}.tar.gz"
        archive_path = os.path.join("downloads", archive_name)
        
        if not os.path.exists(archive_path):
            shutil.make_archive(
                base_name=os.path.join("downloads", job_id),
                format='gztar',
                root_dir=job["workspace"]
            )
        
        job["download_url"] = f"/downloads/{archive_name}"

    return job 

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)