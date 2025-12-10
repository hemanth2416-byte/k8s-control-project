from kubernetes import client, config

# Load Kubernetes config (using your ~/.kube/config)
config.load_kube_config()

# API object for Deployments
apps_v1 = client.AppsV1Api()

# List all deployments in default namespace
deployments = apps_v1.list_namespaced_deployment(namespace="default")

print("\n=== Deployments in Default Namespace ===")
for d in deployments.items:
    print(f"- {d.metadata.name} (replicas: {d.status.replicas})")
