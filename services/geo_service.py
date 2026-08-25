import logging
import httpx
from typing import Dict, Optional, Tuple

logger = logging.getLogger("geo_service")

# Global toggles to simulate provider outages in testing (Probe 4)
DISABLE_PROVIDER_A = False
DISABLE_PROVIDER_B = False

# Mock responses for deterministic testing
# Can be configured as Tuple[str, str] (country, city)
MOCK_PROVIDER_A_RESPONSE: Optional[Tuple[str, str]] = None
MOCK_PROVIDER_B_RESPONSE: Optional[Tuple[str, str]] = None

# We'll use a short timeout so outages don't block requests
TIMEOUT = 2.0

async def get_ip_geolocation(ip: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Looks up geolocation for the given IP address using a fallback chain:
    Provider A (ip-api.com) -> Provider B (ipapi.co) -> Graceful degradation (None)
    
    Returns:
        Tuple[country, city, provider]
    """
    global DISABLE_PROVIDER_A, DISABLE_PROVIDER_B, MOCK_PROVIDER_A_RESPONSE, MOCK_PROVIDER_B_RESPONSE
    
    # Handle local loopback IP addresses for development and local testing
    if ip in ("127.0.0.1", "::1", "localhost", "testclient"):
        # For local dev, simulate lookup using a public IP (Google DNS) so we can see real data
        ip = "8.8.8.8"
        logger.info(f"Loopback IP detected. Simulating geolocation using IP: {ip}")

    # --- Provider A: ip-api.com ---
    if not DISABLE_PROVIDER_A:
        if MOCK_PROVIDER_A_RESPONSE is not None:
            country, city = MOCK_PROVIDER_A_RESPONSE
            logger.info(f"MOCK Geolocation enriched by Provider A (ip-api.com): {country}, {city}")
            return country, city, "ip-api.com"
            
        try:
            url = f"http://ip-api.com/json/{ip}"
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        country = data.get("country")
                        city = data.get("city")
                        logger.info(f"Geolocation enriched by Provider A (ip-api.com): {country}, {city}")
                        return country, city, "ip-api.com"
                    else:
                        logger.warning(f"Provider A returned fail status for IP {ip}: {data.get('message')}")
                else:
                    logger.warning(f"Provider A returned status code {response.status_code}")
        except Exception as e:
            logger.error(f"Provider A failed with error: {str(e)}")
    else:
        logger.info("Provider A is disabled (simulated outage).")

    # --- Provider B: ipapi.co (Fallback) ---
    if not DISABLE_PROVIDER_B:
        if MOCK_PROVIDER_B_RESPONSE is not None:
            country, city = MOCK_PROVIDER_B_RESPONSE
            logger.info(f"MOCK Geolocation enriched by Provider B (ipapi.co): {country}, {city}")
            return country, city, "ipapi.co"
            
        try:
            url = f"https://ipapi.co/{ip}/json/"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if "error" not in data:
                        country = data.get("country_name")
                        city = data.get("city")
                        logger.info(f"Geolocation enriched by Provider B (ipapi.co): {country}, {city}")
                        return country, city, "ipapi.co"
                    else:
                        logger.warning(f"Provider B returned error for IP {ip}: {data.get('reason')}")
                else:
                    logger.warning(f"Provider B returned status code {response.status_code}")
        except Exception as e:
            logger.error(f"Provider B failed with error: {str(e)}")
    else:
        logger.info("Provider B is disabled (simulated outage).")

    # --- Fallback/Degradation: Both failed ---
    logger.warning(f"All geo providers failed or are disabled for IP: {ip}. Degrading gracefully.")
    return None, None, None
