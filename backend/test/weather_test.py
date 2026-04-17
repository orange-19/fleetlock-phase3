import asyncio
import sys
from pathlib import Path

# Add parent directory to Python path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(parent_dir / ".env")

from app.integrations.weather_client import WeatherClient

async def main():
    client = WeatherClient()
    data = await client.get_weather_for_zone("ZONE_CHENNAI_N")
    print("✅ Weather Integration Working!")
    print(data)

asyncio.run(main())