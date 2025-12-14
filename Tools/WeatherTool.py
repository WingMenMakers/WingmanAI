import requests
import geocoder
from geopy.geocoders import Nominatim
from typing import Optional, Dict, Union, Any
from datetime import datetime
import pytz
import logging

class LocationError(Exception):
    pass

class WeatherApiError(Exception):
    pass

class WeatherTool:
    def __init__(self):
        # Use a descriptive user agent
        self.geolocator = Nominatim(user_agent="wingman_weather_agent")

    def figure_out_location(self, location_data: dict) -> Dict[str, float]:
        """
        Determine coordinates based on location data.
        Returns coordinates dict on success, raises LocationError on failure.
        """
        try:
            if location_data.get("current_location"):
                coords = self.get_current_gps_coordinates()
            elif location_data.get("location"):
                coords = self.get_location_gps_coordinates(location_data["location"])
            else:
                raise LocationError("Location data is missing required keys.")
            
            if coords is None:
                raise LocationError(f"Could not determine coordinates for '{location_data.get('location', 'current location')}'.")
            
            return coords
            
        except Exception as e:
            # Catch internal exceptions and wrap them in a Tool-specific error
            logging.error(f"Failed to figure out location: {e}")
            raise LocationError(f"Location resolution failed: {e}")

    def get_current_gps_coordinates(self) -> Optional[Dict[str, float]]:
        """Get current location coordinates using IP geolocation."""
        g = geocoder.ip('me')
        if g.latlng:
            return {"latitude": g.latlng[0], "longitude": g.latlng[1]}
        return None

    def get_location_gps_coordinates(self, location_name: str) -> Optional[Dict[str, float]]:
        """Get coordinates for a specified location name."""
        # Use a timeout for robustness against slow lookups
        location = self.geolocator.geocode(location_name, exactly_one=True, addressdetails=True, timeout=10)
        if location:
            return {"latitude": location.latitude, "longitude": location.longitude}
        return None

    def get_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Get weather data for provided GPS coordinates.
        Returns the raw weather data dictionary on success, raises WeatherApiError on failure.
        """
        # Get timezone for the location
        timezone_str = self._get_timezone(latitude, longitude)
        
        # Build Open-Meteo URL
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}&longitude={longitude}"
            f"&current=temperature_2m,cloudcover,precipitation,rain,relative_humidity_2m,wind_speed_10m,weather_code"
            f"&timezone={timezone_str}"
        )

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "current" in data:
                # Add local time to the response for the Agent's use
                current_data = data["current"]
                
                # Check for "timezone" in the response data for accurate time conversion
                api_timezone = data.get("timezone", timezone_str) 
                
                current_data["local_time"] = datetime.now(pytz.timezone(api_timezone)).strftime("%Y-%m-%d %H:%M:%S")
                current_data["location_timezone"] = api_timezone
                
                # We return the raw dictionary
                return current_data
            
            # Unexpected format, raise a Tool-specific error
            raise self.WeatherApiError("Unexpected API response format for weather data.")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching weather data: {e}")
            raise self.WeatherApiError(f"API request failed: {e}")

    def _get_timezone(self, latitude: float, longitude: float) -> str:
        """Get timezone string for given coordinates, always returning a string."""
        # Fallback to a standard list of timezones if auto fails, or just return the auto result.
        try:
            # We call Open-Meteo with timezone=auto to get the determined timezone string
            url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&timezone=auto&current=temperature_2m"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if "timezone" in data:
                return data["timezone"]
        except:
            # Silent fallback on failure
            pass
            
        # Default to a safe, universal timezone if detection fails
        return "GMT"
    