import json
from kafka import KafkaConsumer
from kubernetes import client, config
from kubernetes.client import Configuration

# ----------------------------
# Load Kubernetes config
# ----------------------------
config.load_kube_config()
c = Configuration.get_default_copy()
c.timeout_seconds = 5
Configuration.set_default(c)

apps_v1 = client.AppsV1Api()

# ----------------------------
# Kafka Consumer
# ----------------------------
consumer = KafkaConsumer(
    "k8s-actions",
    bootstrap_servers="localhost:9092",
    value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
    auto_offset_reset="earliest",
    group_id="k8s-controller",
)

print("Kafka Consumer listening on topic 'k8s-actions'...")


# ----------------------------
# MAIN LOOP
# ----------------------------
for message in consumer:

    raw_value = message.value

    # Skip empty or invalid messages
    if raw_value is None or raw_value == "" or raw_value == b"":
        print("Skipped empty Kafka message.")
        continue

    event = raw_value

    print("\nReceived event:", event)

    action = event.get("action")
    deployment = event.get("deployment")

    # ================================================================
    # 1️⃣ SCALE Deployment
    # ================================================================
    if action == "scale":
        replicas = event.get("replicas")
        print(f"Scaling {deployment} to {replicas} replicas...")

        body = {"spec": {"replicas": replicas}}

        apps_v1.patch_namespaced_deployment(
            name=deployment,
            namespace="default",
            body=body
        )

        print("Scale applied successfully.")

    # ================================================================
    # 2️⃣ DELETE Deployment
    # ================================================================
    elif action == "delete":
        print(f"Deleting deployment {deployment}...")

        apps_v1.delete_namespaced_deployment(
            name=deployment,
            namespace="default"
        )

        print("Deployment deleted successfully.")

    # ================================================================
    # 3️⃣ STATUS of Deployment
    # ================================================================
    elif action == "status":
        print(f"Fetching status for {deployment}...")

        d = apps_v1.read_namespaced_deployment(deployment, "default")

        status_output = {
            "name": d.metadata.name,
            "desired": d.spec.replicas,
            "ready": d.status.ready_replicas
        }

        print("Status:", status_output)

    # ================================================================
    # 4️⃣ UPDATE RESOURCES (CPU / Memory)
    # ================================================================
    elif action == "resources":
        cpu_request = event.get("cpu_request")
        cpu_limit = event.get("cpu_limit")
        mem_request = event.get("mem_request")
        mem_limit = event.get("mem_limit")

        print(f"Updating resources for {deployment}...")

        # Extract actual container name ("api1" or "api2")
        container_name = deployment.split("-")[0]

        patch_body = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": container_name,
                            "resources": {
                                "requests": {},
                                "limits": {}
                            }
                        }]
                    }
                }
            }
        }

        container = patch_body["spec"]["template"]["spec"]["containers"][0]

        # Only patch fields provided by UI
        if cpu_request:
            container["resources"]["requests"]["cpu"] = cpu_request

        if mem_request:
            container["resources"]["requests"]["memory"] = mem_request

        if cpu_limit:
            container["resources"]["limits"]["cpu"] = cpu_limit

        if mem_limit:
            container["resources"]["limits"]["memory"] = mem_limit

        # Apply patch
        apps_v1.patch_namespaced_deployment(
            name=deployment,
            namespace="default",
            body=patch_body
        )

        print(f"Resources updated successfully for {deployment}")

    # ================================================================
    # Finished event
    # ================================================================
    print("Action processed:", event)



