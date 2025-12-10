from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import os
import json

from kubernetes import client, config
from kubernetes.client import Configuration

from kafka import KafkaProducer


# ----------------------------
# Kubernetes Setup
# ----------------------------
try:
    # Try to load kubeconfig from default location
    kube_path = os.path.expanduser("~/.kube/config")
    if os.path.exists(kube_path):
        config.load_kube_config(config_file=kube_path)
    else:
        # Try to load from environment variable (for cloud deployment)
        kube_path = os.getenv("KUBECONFIG")
        if kube_path and os.path.exists(kube_path):
            config.load_kube_config(config_file=kube_path)
        else:
            # Last resort: try in-cluster config (if running in K8s)
            config.load_incluster_config()
except Exception as e:
    print(f"⚠ Kubernetes config load failed: {e}")
    print("  Dashboard will show limited functionality")

cfg = Configuration.get_default_copy()
cfg.timeout_seconds = 5
Configuration.set_default(cfg)

apps_v1 = client.AppsV1Api()
v1 = client.CoreV1Api()
custom_api = client.CustomObjectsApi()


# ----------------------------
# FastAPI Setup
# ----------------------------
app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ----------------------------
# Kafka Producer
# ----------------------------
producer = None
try:
    producer = KafkaProducer(
        bootstrap_servers="localhost:9092",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        request_timeout_ms=3000
    )
    print("✓ Kafka Producer connected")
except Exception as e:
    print(f"⚠ Kafka Producer failed to connect: {e}")
    print("  (Continuing without Kafka - UI will still work)")


# ----------------------------
# ROUTES
# ----------------------------

@app.get("/")
def root():
    return {"message": "K8s Controller API Running"}


@app.get("/ui", response_class=HTMLResponse)
def ui(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# NEW ENDPOINT (for dropdown)
@app.get("/deployment-list")
def deployment_list():
    try:
        deployments = apps_v1.list_namespaced_deployment("default", _request_timeout=5)
        names = [d.metadata.name for d in deployments.items]
        return {"deployments": names}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# Old endpoint (used by your UI if needed)
@app.get("/deployments")
def list_deployments():
    try:
        deployments = apps_v1.list_namespaced_deployment("default", _request_timeout=5)
        out = []
        for d in deployments.items:
            out.append({
                "name": d.metadata.name,
                "desired": d.spec.replicas,
                "ready": d.status.ready_replicas
            })
        return {"deployments": out}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/pod-status/{deployment_name}")
def get_pod_status(deployment_name: str):
    try:
        # Get pods for the deployment
        pods = v1.list_namespaced_pod("default", label_selector=f"app={deployment_name}", _request_timeout=5)
        pod_list = []
        
        for pod in pods.items:
            status = "Pending"
            if pod.status.phase:
                status = pod.status.phase
            
            # Get container readiness status
            ready = False
            if pod.status.conditions:
                for condition in pod.status.conditions:
                    if condition.type == "Ready":
                        ready = condition.status == "True"
                        break
            
            pod_list.append({
                "name": pod.metadata.name,
                "status": status,
                "ready": ready,
                "restarts": pod.status.container_statuses[0].restart_count if pod.status.container_statuses else 0,
                "age": str(pod.metadata.creation_timestamp)
            })
        
        return {"deployment": deployment_name, "pods": pod_list, "count": len(pod_list)}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/pod-logs/{pod_name}")
def get_pod_logs(pod_name: str, lines: int = 100):
    try:
        # Get logs for the pod
        logs = v1.read_namespaced_pod_log("default", pod_name, tail_lines=lines, _request_timeout=5)
        return {"pod": pod_name, "logs": logs}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/deployment-metrics/{deployment_name}")
def get_deployment_metrics(deployment_name: str):
    try:
        # Get pods for the deployment
        pods = v1.list_namespaced_pod("default", label_selector=f"app={deployment_name}", _request_timeout=5)
        
        if not pods.items:
            return {"deployment": deployment_name, "pods": [], "total_cpu_request": "0m", "total_memory_request": "0Mi"}
        
        total_cpu_request = 0  # in millicores
        total_memory_request = 0  # in bytes
        pod_list = []
        
        for pod in pods.items:
            pod_cpu = 0
            pod_memory = 0
            
            if pod.spec.containers:
                for container in pod.spec.containers:
                    if container.resources and container.resources.requests:
                        # Parse CPU (e.g., "200m" = 200 millicores)
                        if "cpu" in container.resources.requests:
                            cpu_str = container.resources.requests["cpu"]
                            if "m" in cpu_str:
                                pod_cpu += int(cpu_str.replace("m", ""))
                            else:
                                pod_cpu += int(float(cpu_str) * 1000)
                        
                        # Parse Memory (e.g., "256Mi" = 256 * 1024 * 1024 bytes)
                        if "memory" in container.resources.requests:
                            mem_str = container.resources.requests["memory"]
                            if "Mi" in mem_str:
                                pod_memory += int(mem_str.replace("Mi", "")) * 1024 * 1024
                            elif "Gi" in mem_str:
                                pod_memory += int(mem_str.replace("Gi", "")) * 1024 * 1024 * 1024
                            elif "Ki" in mem_str:
                                pod_memory += int(mem_str.replace("Ki", "")) * 1024
            
            total_cpu_request += pod_cpu
            total_memory_request += pod_memory
            
            pod_list.append({
                "name": pod.metadata.name,
                "cpu_request": f"{pod_cpu}m",
                "memory_request": f"{pod_memory / (1024 * 1024):.0f}Mi"
            })
        
        return {
            "deployment": deployment_name,
            "pods": pod_list,
            "total_cpu_request": f"{total_cpu_request}m",
            "total_memory_request": f"{total_memory_request / (1024 * 1024):.0f}Mi",
            "pod_count": len(pod_list)
        }
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/deployment-revisions/{deployment_name}")
def get_deployment_revisions(deployment_name: str):
    try:
        import subprocess
        # Get revision history
        result = subprocess.run(
            ["kubectl", "rollout", "history", f"deployment/{deployment_name}", "-n", "default"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return JSONResponse(content={"error": result.stderr}, status_code=500)
        
        lines = result.stdout.strip().split('\n')
        revisions = []
        
        # Parse revision history output
        for i, line in enumerate(lines[1:]):  # Skip header
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    revisions.append({
                        "revision": parts[0],
                        "change_cause": " ".join(parts[1:]) if len(parts) > 1 else ""
                    })
        
        return {"deployment": deployment_name, "revisions": revisions}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/rollback-deployment")
def rollback_deployment(deployment: str = Form(...), revision: str = Form(...)):
    try:
        import subprocess
        # Rollback to specific revision
        result = subprocess.run(
            ["kubectl", "rollout", "undo", f"deployment/{deployment}", "--to-revision=" + revision, "-n", "default"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return JSONResponse(content={"error": result.stderr, "status": "failed"}, status_code=500)
        
        return {"status": "success", "message": f"Rolled back {deployment} to revision {revision}"}
    except Exception as e:
        return JSONResponse(content={"error": str(e), "status": "failed"}, status_code=500)


@app.get("/deployment-events/{deployment_name}")
def get_deployment_events(deployment_name: str):
    try:
        # Get events for the deployment
        events = v1.list_namespaced_event("default", field_selector=f"involvedObject.name={deployment_name}", _request_timeout=5)
        
        event_list = []
        for event in events.items:
            event_list.append({
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "count": event.count,
                "first_timestamp": str(event.first_timestamp),
                "last_timestamp": str(event.last_timestamp),
                "involved_object": {
                    "name": event.involved_object.name,
                    "kind": event.involved_object.kind,
                    "namespace": event.involved_object.namespace
                }
            })
        
        # Sort by last timestamp (most recent first)
        event_list.sort(key=lambda x: x["last_timestamp"], reverse=True)
        
        return {"deployment": deployment_name, "events": event_list}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/hpa-config/{deployment_name}")
def get_hpa_config(deployment_name: str):
    try:
        # Try to get existing HPA for deployment
        hpas = custom_api.list_namespaced_custom_object(
            "autoscaling", "v2", "default", "horizontalpodautoscalers",
            field_selector=f"spec.scaleTargetRef.name={deployment_name}",
            _request_timeout=5
        )
        
        if hpas.get("items"):
            hpa = hpas["items"][0]
            spec = hpa.get("spec", {})
            return {
                "deployment": deployment_name,
                "exists": True,
                "min_replicas": spec.get("minReplicas", 1),
                "max_replicas": spec.get("maxReplicas", 10),
                "cpu_threshold": spec.get("metrics", [{}])[0].get("resource", {}).get("target", {}).get("averageUtilization", 80)
            }
        else:
            return {
                "deployment": deployment_name,
                "exists": False,
                "min_replicas": 1,
                "max_replicas": 10,
                "cpu_threshold": 80
            }
    except Exception as e:
        return {
            "deployment": deployment_name,
            "exists": False,
            "min_replicas": 1,
            "max_replicas": 10,
            "cpu_threshold": 80,
            "error": str(e)
        }


@app.post("/create-hpa")
def create_hpa(deployment: str = Form(...), min_replicas: int = Form(...), max_replicas: int = Form(...), cpu_threshold: int = Form(...)):
    try:
        import subprocess
        
        # Create HPA using kubectl
        hpa_yaml = f"""
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {deployment}-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {deployment}
  minReplicas: {min_replicas}
  maxReplicas: {max_replicas}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {cpu_threshold}
"""
        
        result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=hpa_yaml,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return JSONResponse(content={"error": result.stderr, "status": "failed"}, status_code=500)
        
        return {"status": "success", "message": f"HPA created for {deployment}"}
    except Exception as e:
        return JSONResponse(content={"error": str(e), "status": "failed"}, status_code=500)


@app.get("/cluster-stats")
def get_cluster_stats():
    try:
        deployments = apps_v1.list_namespaced_deployment("default", _request_timeout=5)
        pods = v1.list_namespaced_pod("default", _request_timeout=5)
        
        total_pods = len(pods.items)
        running_pods = sum(1 for pod in pods.items if pod.status.phase == "Running")
        pending_pods = sum(1 for pod in pods.items if pod.status.phase == "Pending")
        failed_pods = sum(1 for pod in pods.items if pod.status.phase == "Failed")
        
        total_cpu = 0
        total_memory = 0
        
        for pod in pods.items:
            if pod.spec.containers:
                for container in pod.spec.containers:
                    if container.resources and container.resources.requests:
                        if "cpu" in container.resources.requests:
                            cpu_str = container.resources.requests["cpu"]
                            if "m" in cpu_str:
                                total_cpu += int(cpu_str.replace("m", ""))
                            else:
                                total_cpu += int(float(cpu_str) * 1000)
                        
                        if "memory" in container.resources.requests:
                            mem_str = container.resources.requests["memory"]
                            if "Mi" in mem_str:
                                total_memory += int(mem_str.replace("Mi", "")) * 1024 * 1024
                            elif "Gi" in mem_str:
                                total_memory += int(mem_str.replace("Gi", "")) * 1024 * 1024 * 1024
                            elif "Ki" in mem_str:
                                total_memory += int(mem_str.replace("Ki", "")) * 1024
        
        return {
            "deployments": len(deployments.items),
            "total_pods": total_pods,
            "running_pods": running_pods,
            "pending_pods": pending_pods,
            "failed_pods": failed_pods,
            "total_cpu_requested": f"{total_cpu}m",
            "total_memory_requested": f"{total_memory / (1024 * 1024):.0f}Mi"
        }
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/send")
def send_message(
    action: str = Form(...),
    deployment: str = Form(...),
    replicas: int = Form(None),
    cpu_request: str = Form(None),
    cpu_limit: str = Form(None),
    mem_request: str = Form(None),
    mem_limit: str = Form(None),
):
    msg = {"action": action, "deployment": deployment}

    # Scale
    if replicas is not None:
        msg["replicas"] = replicas

    # Resource update
    if action == "resources":
        if cpu_request:
            msg["cpu_request"] = cpu_request
        if cpu_limit:
            msg["cpu_limit"] = cpu_limit
        if mem_request:
            msg["mem_request"] = mem_request
        if mem_limit:
            msg["mem_limit"] = mem_limit

    print("Sending Kafka message:", msg)

    if producer:
        try:
            producer.send("k8s-actions", msg)
            producer.flush()
        except Exception as e:
            print(f"Error sending to Kafka: {e}")
    else:
        print("(Kafka not available - message would be sent to queue)")

    return {"status": "sent", "message": msg}


