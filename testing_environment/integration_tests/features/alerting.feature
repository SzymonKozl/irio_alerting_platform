Feature: Alerting
    As a user
	I want to monitor http services
	So that I can be alerted when they go down

    Background:
        Given the alerting platform API is running

    Scenario: Service goes down and alert is triggered
        When I add a "MyApp" service with URL "http://mock-http-service.testing.svc.cluster.local" to the alerting platform
        the service with the URL "http://mock-http-service.testing.svc.cluster.local" becomes unreachable
        Then the alerting platform should send an alert to my email
