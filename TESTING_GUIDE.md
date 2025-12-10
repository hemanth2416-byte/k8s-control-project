# Kubernetes Control Panel - Testing Guide

## Prerequisites
- Ensure Uvicorn is running: `uvicorn main:app --reload` from `controller-api` folder
- Kubernetes cluster is accessible (minikube, docker-desktop, or real cluster)
- At least one deployment exists in the `default` namespace

## Access the Dashboard
1. Open your browser and navigate to: **http://localhost:8000/ui**
2. You should see the enhanced Kubernetes Control Panel with a purple gradient background

---

## Feature 1: Scale Deployment

### How to Test:
1. Open the dashboard
2. Locate the **"Scale Deployment"** card (first card)
3. Select a deployment from the dropdown
4. Enter a number of replicas (e.g., 3, 5, etc.)
5. Click **"Scale"** button

### Expected Results:
- Button should show success feedback
- In a terminal, run: `kubectl get deployments -n default` to verify replica count changed
- Kafka message should be sent to the broker

### Example Command:
```bash
kubectl get deployments -n default
kubectl get pods -n default
```

---

## Feature 2: Delete Deployment

### How to Test:
1. On the dashboard, find **"Delete Deployment"** card
2. Select a non-critical deployment from dropdown
3. Click **"Confirm Delete"** button
4. Confirm the action if prompted

### Expected Results:
- Deployment should be deleted from the cluster
- Verify with: `kubectl get deployments -n default`
- The deployment should no longer appear in dropdowns after refresh (F5)

---

## Feature 3: Get Deployment Status (Basic)

### How to Test:
1. Find **"Get Deployment Status"** card
2. Select a deployment
3. Click **"Check Status"** button

### Expected Results:
- Form submits to the backend
- Kafka message is sent indicating status check action

---

## Feature 4: Update Resources (CPU/Memory)

### How to Test:
1. Locate **"Update Resources"** card
2. Select a deployment
3. Fill in resource values:
   - CPU Request: `250m`
   - CPU Limit: `500m`
   - Memory Request: `128Mi`
   - Memory Limit: `256Mi`
4. Click **"Update Resources"** button

### Expected Results:
- Form data submitted to backend
- Kafka message created with resource configuration
- In terminal: `kubectl get deployment <name> -o yaml` to see resource spec

### Example:
```bash
kubectl get deployment api1 -o yaml | grep -A 10 "resources:"
```

---

## Feature 5: View Pod Status (NEW)

### How to Test:
1. Find **"View Pod Status"** card (cyan gradient)
2. Select a deployment from the dropdown
3. Click **"Show Pods"** button
4. A modal should appear listing all pods

### Expected Results:
- Modal shows pod name, status, ready state (✓ or ✗), and restart count
- Status badges show:
  - **Green**: Running
  - **Orange**: Pending
  - **Red**: Failed/Other
- Close modal by clicking the X or outside the modal

### Verify in Terminal:
```bash
kubectl get pods -n default
kubectl describe pod <pod-name> -n default
```

---

## Feature 6: View Pod Logs (NEW)

### How to Test:
1. Find **"View Pod Logs"** card (orange-yellow gradient)
2. Select a deployment
3. Click **"View Logs"** button
4. Modal appears with list of pods - click on a pod name
5. Second modal shows the pod's logs in a dark terminal theme

### Expected Results:
- Pod list shows all running pods
- Logs display in a monospace font with dark background
- Last 200 lines of logs shown
- Logs are properly escaped (no HTML injection)

### Verify in Terminal:
```bash
kubectl logs <pod-name> -n default
kubectl logs <pod-name> -n default --tail=200
```

---

## Feature 7: Resource Usage Dashboard (NEW)

### How to Test:
1. Find **"Resource Usage"** card (teal-pink gradient)
2. Select a deployment
3. Click **"View Metrics"** button
4. Modal displays resource metrics

### Expected Results:
- Shows total CPU requested (in millicores with 'm')
- Shows total Memory requested (in MiB)
- Displays pod count
- Lists each pod with individual CPU and Memory requests
- Pod breakdown shows:
  - Pod name
  - CPU request (e.g., 200m)
  - Memory request (e.g., 256Mi)

### Verify with:
```bash
kubectl get pods -n default -o json | jq '.items[].spec.containers[].resources.requests'

# Or describe a deployment:
kubectl describe deployment <name> -n default
```

### Example Output Expected:
```
Total CPU Requested: 400m
Total Memory Requested: 512Mi
Pod Breakdown:
- api1-xyz123: CPU: 200m, Memory: 256Mi
- api1-abc456: CPU: 200m, Memory: 256Mi
```

---

## Quick Testing Workflow

### Setup Test Deployments:
```bash
# If you don't have deployments, create test ones:
kubectl create deployment api1 --image=nginx --replicas=2 -n default
kubectl create deployment api2 --image=nginx --replicas=1 -n default

# Set resource requests (optional):
kubectl set resources deployment api1 --requests=cpu=200m,memory=256Mi -n default
```

### Test All Features in Order:
1. **View Pod Status** - Check current state
2. **View Pod Logs** - Read pod output
3. **Resource Usage** - See resource allocation
4. **Scale Deployment** - Change replicas to 5
5. **View Pod Status Again** - Confirm scaling worked
6. **Resource Usage Again** - See new total resources

---

## Troubleshooting

### Feature Not Working?

#### Pod Status Returns Empty:
- Verify pod labels match `app=<deployment-name>`
- Check: `kubectl get pods -L app -n default`

#### No Logs Appear:
- Ensure pod has been running (logs may not be available immediately)
- Check if pod is in CrashLoopBackOff: `kubectl describe pod <name>`

#### Resource Metrics Show 0:
- Verify deployment has resource requests defined
- Set resources: `kubectl set resources deployment <name> --requests=cpu=100m,memory=128Mi`

#### Dropdowns Empty:
- Ensure deployments exist: `kubectl get deployments -n default`
- Check CoreV1Api access in backend

---

## Performance Notes

- **Pod Status**: Real-time query, should return within 1 second
- **Logs**: Fetches 200 lines, ~2-5 second latency depending on log volume
- **Metrics**: Parses container requests, instant response

---

## Next Steps After Testing

Once all features work:
1. Add **Rollback Deployment** feature
2. Add **Auto-scaling Configuration** feature
3. Add **Events Timeline** feature
4. Deploy to production cluster

---

## API Endpoints Reference

| Feature | Endpoint | Method |
|---------|----------|--------|
| List Deployments | `/deployment-list` | GET |
| Pod Status | `/pod-status/{deployment}` | GET |
| Pod Logs | `/pod-logs/{pod-name}` | GET |
| Resource Metrics | `/deployment-metrics/{deployment}` | GET |
| Send Actions | `/send` | POST |
| UI Dashboard | `/ui` | GET |

