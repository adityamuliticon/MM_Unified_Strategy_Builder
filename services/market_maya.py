import requests
import json
from config import Config

class MarketMayaService:
    def __init__(self):
        self.token = Config.MARKET_MAYA_BEARER_TOKEN
        if self.token and not self.token.startswith("Bearer "):
            self.token = f"Bearer {self.token}"

    def deploy_strategy(self, payload):
        """
        Deploys a strategy to Market Maya and logs the payload.
        """
        # Log the payload to a file
        from datetime import datetime
        try:
            with open("deployed_strategies.log", "a") as f:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "strategy_name": payload.get("strategyName", "Unknown"),
                    "payload": payload
                }
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Logging error: {e}")

        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        json_payload = json.dumps(payload)
        # Construct curl command for fallback and debugging
        curl_cmd = f"curl -X POST {Config.CREATE_STRATEGY_URL} -H 'Authorization: {self.token}' -H 'Content-Type: application/json' -d '{json_payload}'"
        print(f"\n[DEBUG] Deployment CURL Command:\n{curl_cmd}\n")

        try:
            url = Config.CREATE_STRATEGY_URL
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return {"status": "success", "data": response.json()}
            else:
                # If it's a 400, the payload is invalid. Fallback to curl is only useful 
                # if we suspect requests is mangling the format.
                print(f"Requests failed (Status {response.status_code}): {response.text}")
                return {"status": "error", "code": response.status_code, "message": response.text}
        except Exception as e:
            print(f"Connection error: {e}. Attempting shell curl fallback...")
            import subprocess
            result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    return {"status": "success", "data": json.loads(result.stdout)}
                except:
                    return {"status": "success", "raw_output": result.stdout}
            return {"status": "error", "message": str(e)}

# Singleton instance
market_maya = MarketMayaService()
