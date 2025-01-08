Feature: Number API
	As a user
	I want to add numbers to a list and view the list
	So that I can manage my numbers in the Number API

	Scenario: Add a number to the list
		Given the API is running
		When I add the number 42
		Then I should see a list containing number 42

	Scenario: View the list of numbers
		Given the API is running
		When I request the list of numbers
		Then I should see a list of numbers
