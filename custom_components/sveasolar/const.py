DOMAIN = "sveasolar"
CONFIG_FLOW_TITLE = "Svea Solar"
CONF_REFRESH_TOKEN = "refresh_token"
SYSTEM_TYPE_BATTERY = "battery"
SYSTEM_TYPE_LOCATION = "location"
SYSTEM_TYPE_EV = "ev"

MOCK_DATA = """
{
    "electricVehicles": [
        {
            "id": "788be180-fb82-48f3-b84c-d4eabc522f6b",
            "isConnected": true,
            "name": "RAV4",
            "role": "Owner"
        }
    ],
    "locations": [
        {
            "battery": null,
            "energyContracts": [
                {
                    "id": "b8e49efe-09de-4c3b-bef1-abb52c5f91f0",
                    "isActive": true,
                    "locationId": "ba859c17-2ae6-45bf-a8bb-667f4bb80c8f",
                    "role": "Viewer",
                    "type": "Consumption"
                }
            ],
            "heatPumps": [],
            "id": "ba859c17-2ae6-45bf-a8bb-667f4bb80c8f",
            "name": "Årnebo 27",
            "solar": []
        },
        {
            "battery": {
                "id": "3e3d86e4-a59d-444a-99ee-61224eed814f",
                "imageUrl": "https://app-battery-images.s3.eu-west-1.amazonaws.com/Homevolt-My-system-banner.png",
                "locationId": "85e34fad-d32f-4748-a643-455f334b1c6e",
                "name": "Homevolt",
                "role": "Owner"
            },
            "energyContracts": [],
            "heatPumps": [],
            "id": "85e34fad-d32f-4748-a643-455f334b1c6e",
            "name": "ÅRNEBO 27",
            "solar": []
        }
    ]
}
"""