from core.engine import get_weather_data

def main():
    print("Initializing Weather App...")
    data = get_weather_data("San Francisco")
    print(f"Weather Report: {data}")

if __name__ == "__main__":
    main()