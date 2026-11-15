import sys, requests
from dotenv import dotenv_values
s = dotenv_values("/app/backend/.env")["CLERK_SECRET_KEY"]
h = {"Authorization": f"Bearer {s}", "User-Agent": "emergent-test"}
for uid in sys.argv[1:]:
    r = requests.post("https://api.clerk.com/v1/sign_in_tokens", json={"user_id": uid, "expires_in_seconds": 900}, headers=h, timeout=20)
    print(r.json()["token"])
