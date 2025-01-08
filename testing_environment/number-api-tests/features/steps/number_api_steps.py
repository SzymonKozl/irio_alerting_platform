import requests
from behave import given, when, then

BASE_URL = "http://34.56.138.14"

@given("the API is running")
def step_api_is_running(context):
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@when("I add the number {number:d}")
def step_add_number(context, number):
    response = requests.post(f"{BASE_URL}/add", json={"number": number})
    assert response.status_code == 201
    context.response = response.json()

@then("I should see a list containing number {number:d}")
def step_list_contains_number(context, number):
    response = requests.get(f"{BASE_URL}/list")
    assert response.status_code == 200
    numbers = response.json()["list"]
    assert number in numbers

@when("I request the list of numbers")
def step_request_list_of_numbers(context):
    response = requests.get(f"{BASE_URL}/list")
    assert response.status_code == 200
    context.response = response.json()

@then("I should see a list of numbers")
def step_see_list_of_numbers(context):
    numbers = context.response["list"]
    assert isinstance(numbers, list)
