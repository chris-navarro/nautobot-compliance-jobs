import requests
from django.conf import settings

class NautobotClient:
    def __init__(self):
        self.base_url = settings.NAUTOBOT_URL
        self.token = settings.NAUTOBOT_TOKEN
        self.headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def get_devices(self, role=None, site=None):
        """Fetch devices from Nautobot"""
        url = f"{self.base_url}/api/dcim/devices/"
        params = {"status": "active", "has_primary_ip": "true"}
        
        if role:
            params["role"] = role
        if site:
            params["site"] = site
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()["results"]
    
    def get_device_config(self, device_name):
        """Fetch running config via NAPALM"""
        url = f"{self.base_url}/api/dcim/devices/{device_name}/napalm/"
        payload = {"method": "get_config", "retrieve": "running"}
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()["running"]
    
    def get_golden_config(self, device_name, template_type="base"):
        """Fetch golden template from Git repository"""
        # Implementation depends on Nautobot Golden Config plugin
        pass