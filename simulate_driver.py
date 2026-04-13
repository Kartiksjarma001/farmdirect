import requests
import time

truck_id = 1   # ⚠️ SAME होना चाहिए जो assign किया है

lat = 29.38
lng = 79.45

while True:
    url = f"http://127.0.0.1:5000/update_location/{truck_id}?lat={lat}&lng={lng}"
    
    try:
        requests.get(url)
        print("Location updated:", lat, lng)
    except:
        print("Server not running ❌")

    lat += 0.001
    lng += 0.001

    time.sleep(5)