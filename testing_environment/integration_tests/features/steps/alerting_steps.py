import requests
from behave import given, when, then
from kubernetes import client, config

config.load_kube_config()

def get_service_ip(service_name, namespace="default"):
    v1 = client.CoreV1Api()
    service = v1.read_namespaced_service(service_name, namespace)
    ip = service.status.load_balancer.ingress[0].ip
    print(f"Service IP: {ip}")
    return ip

BASE_URL = get_service_ip("alerting-app-service", "testing")

@given("the alerting platform API is running")
def step_api_is_running(context):
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@when("I add a {name:str} service with URL {url:str} to the alerting platform")
def step_add_service(context, name, url):
    pass

@when("the service with the URL {url:str} becomes unreachable")
def step_kill_service(context, url):
    pass

@then("the alerting platform should send an alert to my email")
def step_verify_email(context):
    pass
