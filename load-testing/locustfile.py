from locust import HttpUser, task, between

class OrderServiceUser(HttpUser):

    wait_time = between(1, 2)

    @task
    def create_order(self):
        self.client.post("/create-order", json={
            "user_id": "123",
            "item": "pizza",
            "quantity": 1
        })

 