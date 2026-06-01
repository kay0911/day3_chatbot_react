import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

def _get_db_path(filename: str) -> str:
    """Helper to locate JSON database files relative to the project root."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, filename)

def search_rooms(location: str, checkin: str, checkout: str, guests: int) -> List[Dict[str, Any]]:
    """
    Search for available hotel rooms/packages in a location for a date range and guest count.
    
    Args:
        location: The city or area (e.g. "Nha Trang")
        checkin: Check-in date string (YYYY-MM-DD)
        checkout: Check-out date string (YYYY-MM-DD)
        guests: Total number of guests
    """
    db_path = _get_db_path("packages.json")
    if not os.path.exists(db_path):
        return []
        
    with open(db_path, "r", encoding="utf-8") as f:
        packages = json.load(f)
        
    # Generate stay dates (nights)
    try:
        checkin_dt = datetime.strptime(checkin.strip(), "%Y-%m-%d")
        checkout_dt = datetime.strptime(checkout.strip(), "%Y-%m-%d")
        stay_dates = []
        current_dt = checkin_dt
        while current_dt < checkout_dt:
            stay_dates.append(current_dt.strftime("%Y-%m-%d"))
            current_dt += timedelta(days=1)
    except Exception as e:
        return [{"error": f"Invalid date format: {e}"}]

    available_rooms = []
    location_lower = location.lower().strip()
    
    for pkg in packages:
        # Check location
        if location_lower not in pkg.get("location", "").lower():
            continue
            
        # Check capacity
        max_capacity = pkg.get("max_adults", 0) + pkg.get("max_children", 0)
        if guests > max_capacity:
            continue
            
        # Check date availability (blocked_dates overlap)
        blocked_dates = pkg.get("blocked_dates", [])
        is_blocked = False
        for date_str in stay_dates:
            if date_str in blocked_dates:
                is_blocked = True
                break
                
        if not is_blocked:
            available_rooms.append(pkg)
            
    return available_rooms

def search_nearby_attractions(location: str, attr_type: str) -> List[Dict[str, Any]]:
    """
    Search for local attractions by location and type.
    Uses Fuzzy Keyword mapping for Vietnamese queries.
    
    Args:
        location: The location of the attractions
        attr_type: The type of attraction requested (e.g. "ca nhạc", "spa")
    """
    db_path = _get_db_path("attractions.json")
    if not os.path.exists(db_path):
        return []
        
    with open(db_path, "r", encoding="utf-8") as f:
        attractions = json.load(f)
        
    matching_attractions = []
    location_lower = location.lower().strip()
    req_type_lower = attr_type.lower().strip()
    
    for attr in attractions:
        # Check location
        if location_lower not in attr.get("location", "").lower():
            continue
            
        is_match = False
        attr_type_lower = attr.get("type", "").lower()
        attr_name_lower = attr.get("name", "").lower()
        
        # Fuzzy Semantic matching from individual report
        if "show" in req_type_lower or "diễn" in req_type_lower or "ca nhạc" in req_type_lower:
            if "show" in attr_type_lower or "show" in attr_name_lower:
                is_match = True
        elif "spa" in req_type_lower or "trị liệu" in req_type_lower or "tắm" in req_type_lower:
            if "spa" in attr_type_lower or "spa" in attr_name_lower:
                is_match = True
        else:
            # Fallback direct substring match
            if req_type_lower in attr_type_lower or req_type_lower in attr_name_lower:
                is_match = True
                
        if is_match:
            matching_attractions.append(attr)
            
    return matching_attractions

def filter_packages(packages: Any, includes: Any) -> List[Dict[str, Any]]:
    """
    Filter packages to only those containing all requested amenities/features.
    
    Args:
        packages: A list of room package dictionaries
        includes: A list of string amenities/features to check
    """
    # Robust parsing of packages if they are passed as string representation
    if isinstance(packages, str):
        import ast
        try:
            packages = ast.literal_eval(packages)
        except Exception as e:
            return [{"error": f"Failed to parse packages string in filter_packages: {e}"}]
            
    if isinstance(includes, str):
        import ast
        try:
            includes = ast.literal_eval(includes)
        except Exception:
            includes = [includes]
            
    if not isinstance(packages, list):
        return [{"error": f"packages must be a list, got {type(packages)}"}]
        
    if not isinstance(includes, list):
        includes = [includes]
        
    filtered = []
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
            
        pkg_includes = [x.lower().strip() for x in pkg.get("includes", [])]
        match = True
        for inc in includes:
            if not isinstance(inc, str):
                continue
            if inc.lower().strip() not in pkg_includes:
                match = False
                break
        if match:
            filtered.append(pkg)
            
    return filtered
