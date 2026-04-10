import requests
api_key = "4234fb95b48e4a558d6204018262501"
url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q=London&days=14&aqi=yes&alerts=yes"
try:
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success")
        data = response.json()
        print(f"Location: {data.get('location', {}).get('name')}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
