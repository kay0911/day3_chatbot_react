import json
import os
from typing import List, Dict, Any, Optional

# Path to the mock database
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "packages.json")

def load_data() -> Dict[str, Any]:
    """Helper function to load the packages database."""
    if not os.path.exists(DATA_FILE):
        return {"packages": [], "attractions": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"packages": [], "attractions": []}

def search_vinpearl_packages(location: str = "Nha Trang", check_in: str = "", check_out: str = "", adults: int = 2, children: int = 0) -> List[Dict[str, Any]]:
    """
    Tìm kiếm các gói nghỉ dưỡng (combo) tại Vinpearl Nha Trang phù hợp với số lượng khách (người lớn và trẻ em).
    
    Args:
        location: Địa điểm tìm kiếm (ví dụ: 'Nha Trang').
        check_in: Ngày nhận phòng dạng YYYY-MM-DD (ví dụ: '2026-06-05').
        check_out: Ngày trả phòng dạng YYYY-MM-DD (ví dụ: '2026-06-07').
        adults: Số người lớn.
        children: Số trẻ em đi kèm.
        
    Returns:
        Danh sách các gói phòng/combo còn trống phù hợp sức chứa.
    """
    data = load_data()
    matching_packages = []
    
    for pkg in data.get("packages", []):
        # Lọc theo địa điểm (không phân biệt hoa thường)
        if location.lower() not in pkg.get("location", "").lower():
            continue
            
        # Lọc theo sức chứa tối đa
        if adults <= pkg.get("max_adults", 99) and children <= pkg.get("max_children", 99):
            matching_packages.append(pkg)
            
    return matching_packages

def search_rooms(location: str = "Nha Trang", min_price: float = 0, max_price: float = 99999999, check_in: str = "", check_out: str = "", adults: int = 2, children: int = 0) -> List[Dict[str, Any]]:
    """
    Tìm kiếm các gói phòng trong khoảng giá từ min_price đến max_price tại địa điểm mong muốn và có sức chứa phù hợp.
    
    Args:
        location: Địa điểm tìm kiếm (ví dụ: 'Nha Trang').
        min_price: Giá tối thiểu mỗi đêm (VNĐ).
        max_price: Giá tối đa mỗi đêm (VNĐ).
        check_in: Ngày nhận phòng dạng YYYY-MM-DD.
        check_out: Ngày trả phòng dạng YYYY-MM-DD.
        adults: Số người lớn.
        children: Số trẻ em.
        
    Returns:
        Danh sách các gói phòng/combo trong tầm giá và có đủ sức chứa.
    """
    data = load_data()
    matching_rooms = []
    
    for pkg in data.get("packages", []):
        if location.lower() not in pkg.get("location", "").lower():
            continue
            
        price = pkg.get("price_per_night", 0)
        if min_price <= price <= max_price:
            if adults <= pkg.get("max_adults", 99) and children <= pkg.get("max_children", 99):
                matching_rooms.append(pkg)
                
    return matching_rooms

def search_nearby_attractions(location: str = "Nha Trang", attraction_type: str = "") -> List[Dict[str, Any]]:
    """
    Tìm kiếm các địa điểm vui chơi, ăn uống, nhà hàng, spa xung quanh khu vực.
    
    Args:
        location: Khu vực tìm kiếm (ví dụ: 'Nha Trang' hoặc 'Hòn Tre').
        attraction_type: Loại địa điểm cần tìm (ví dụ: 'Amusement Park', 'Show', 'Restaurant', 'Spa', 'Museum', 'Beach').
                         Để trống nếu muốn tìm tất cả.
                         
    Returns:
        Danh sách địa điểm xung quanh khớp với từ khóa tìm kiếm.
    """
    data = load_data()
    matching_attractions = []
    
    for attr in data.get("attractions", []):
        # Lọc theo địa điểm hoặc khoảng cách có chứa Nha Trang
        in_location = (location.lower() in attr.get("location", "").lower()) or ("nha trang" in attr.get("location", "").lower())
        if not in_location:
            continue
            
        if attraction_type:
            if attraction_type.lower() in attr.get("type", "").lower() or attraction_type.lower() in attr.get("name", "").lower():
                matching_attractions.append(attr)
        else:
            matching_attractions.append(attr)
            
    return matching_attractions

def filter_packages(packages: List[Dict[str, Any]], includes: List[str]) -> List[Dict[str, Any]]:
    """
    Lọc danh sách các combo dựa trên danh sách các tiện ích đi kèm bắt buộc (ví dụ: 'VinWonders', 'Buffet Breakfast').
    
    Args:
        packages: Danh sách gói combo cần lọc (thường là kết quả từ search_vinpearl_packages hoặc search_rooms).
        includes: Danh sách các tiện ích bắt buộc phải có trong 'includes' (không phân biệt hoa thường).
        
    Returns:
        Danh sách combo đã lọc thỏa mãn đầy đủ các tiện ích đi kèm.
    """
    filtered = []
    for pkg in packages:
        pkg_includes = [inc.lower() for inc in pkg.get("includes", [])]
        
        # Kiểm tra xem gói có chứa tất cả các tiện ích được yêu cầu không
        match = True
        for req in includes:
            req_lower = req.lower()
            # Kiểm tra xem có chứa từng phần của từ khóa không (ví dụ: 'vinwonders' khớp với 'VinWonders Ticket')
            has_inc = any(req_lower in inc for inc in pkg_includes)
            if not has_inc:
                match = False
                break
                
        if match:
            filtered.append(pkg)
            
    return filtered

def generate_itinerary(duration_days: int = 3, location: str = "Vinpearl Resort Nha Trang", key_activities: List[str] = None) -> List[str]:
    """
    Tự động lập lịch trình vui chơi và nghỉ dưỡng theo ngày dựa trên tiện ích của gói combo đã chọn và các hoạt động chính.
    
    Args:
        duration_days: Số ngày của chuyến đi (ví dụ: 3 ngày).
        location: Khách sạn hoặc resort dừng chân (để tùy chỉnh điểm đến).
        key_activities: Danh sách các hoạt động chính muốn trải nghiệm (ví dụ: ['VinWonders', 'Tata Show', 'Spa']).
        
    Returns:
        Danh sách lịch trình chi tiết theo từng ngày (từ Ngày 1 đến Ngày N).
    """
    if key_activities is None:
        key_activities = []
        
    itinerary = []
    
    # Định nghĩa sẵn một số hoạt động theo ngày để sinh ngẫu nhiên nhưng hợp lý
    activities_pool = {
        "VinWonders": "Dành trọn vẹn thời gian khám phá Thiên đường giải trí VinWonders Nha Trang (vòng quay bầu trời, công viên nước, trò chơi mạo hiểm).",
        "Tata Show": "Thưởng thức siêu phẩm thực cảnh đa phương tiện hoành tráng Tata Show tại Quảng trường Thần thoại lúc 19:30.",
        "Spa": "Thư giãn chăm sóc sức khỏe tại Akoya Spa tinh tế nằm trên chòi gỗ giữa hồ nước tĩnh lặng hoặc bên bờ biển.",
        "Resort Relaxing": "Thư giãn tại bãi biển riêng Tropicana hoang sơ, tắm hồ bơi ngoài trời siêu rộng và thưởng thức cocktail mát lạnh.",
        "Museum": "Đi tàu cao tốc sang đất liền ghé thăm Viện Hải dương học Nha Trang để chiêm ngưỡng thế giới sinh vật biển sinh động.",
        "Dining": "Dùng bữa tối hải sản tươi ngon Nha Trang hoặc buffet Á-Âu thượng hạng tại Nhà hàng Imperial sang trọng."
    }
    
    # Tạo lịch trình cơ bản
    for day in range(1, duration_days + 1):
        day_events = []
        if day == 1:
            day_events.append("14:00 - Làm thủ tục nhận phòng nghỉ tại resort sang trọng.")
            # Tìm kiếm hoạt động thư giãn nhẹ nhàng hoặc ăn tối
            relax_act = [act for act in key_activities if act in ["Resort Relaxing", "Spa", "Dining"]]
            if relax_act:
                day_events.append(f"Chiều - {activities_pool.get(relax_act[0])}")
            else:
                day_events.append("Chiều - Tắm hồ bơi vô cực hoặc dạo bãi biển riêng Tropicana cát trắng trải dài.")
            day_events.append("19:00 - Ăn tối buffet thịnh soạn tại nhà hàng chính của khu resort.")
        elif day == duration_days:
            day_events.append("Sáng - Thức dậy ngắm bình minh trên vịnh biển, tập yoga hoặc tắm biển sớm.")
            day_events.append("08:00 - Thưởng thức buffet sáng tại nhà hàng.")
            day_events.append("10:00 - Mua sắm quà lưu niệm hoặc thư giãn nhẹ nhàng tại chòi nghỉ mát.")
            day_events.append("12:00 - Làm thủ tục trả phòng và đi tàu cao tốc về đất liền, kết thúc kỳ nghỉ tuyệt vời.")
        else:
            # Các ngày ở giữa dành cho hoạt động lớn
            day_events.append("08:00 - Ăn sáng buffet tràn đầy năng lượng tại resort.")
            
            # Ưu tiên các hoạt động lớn như VinWonders, Tata Show
            big_acts = [act for act in key_activities if act in ["VinWonders", "Tata Show", "Museum", "Spa"]]
            if big_acts:
                current_act = big_acts[0]
                day_events.append(f"Trọn ngày - {activities_pool.get(current_act)}")
                key_activities.remove(current_act)
                
                # Nếu có Tata Show, tự động chèn vào buổi tối ngày chơi VinWonders
                if current_act == "VinWonders" or "Tata Show" in key_activities:
                    day_events.append(f"19:30 - {activities_pool.get('Tata Show')}")
                    if "Tata Show" in key_activities:
                        key_activities.remove("Tata Show")
            else:
                # Mặc định đi chơi VinWonders ở ngày giữa
                day_events.append(f"Trọn ngày - {activities_pool.get('VinWonders')}")
                day_events.append(f"19:30 - {activities_pool.get('Tata Show')}")
                
            day_events.append("21:00 - Dạo biển đêm yên bình dưới hàng dừa xanh và nghỉ ngơi tại phòng nghỉ ấm áp.")
            
        itinerary.append(f"Ngày {day}:\n  " + "\n  ".join(day_events))
        
    return itinerary
