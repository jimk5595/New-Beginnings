import requests
import json

def test_run_eliza():
    payload = {
        "model": "gpt-4",
        "prompt": "hello",
        "task_type": "core"
    }
    response = requests.post(
        "http://localhost:8000/run_eliza",
        json=payload
    )
    print(response.json())

if __name__ == "__main__":
    test_run_eliza()
