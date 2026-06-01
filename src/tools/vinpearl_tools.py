import json
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional


DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "vinpearl_nha_trang_inventory.json",
)


CONFIRM_KEYWORDS = [
    "xac nhan dat",
    "dong y dat",
    "chot dat",
    "dat luon",
    "tien hanh dat",
    "confirm booking",
    "confirm",
]


def _normalize(text: str) -> str:
    replacements = {
        "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a",
        "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
        "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "đ": "d",
        "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
        "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "í": "i", "ì": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "ó": "o", "ò": "o", "ỏ": "o", "õ": "o", "ọ": "o",
        "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
        "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "ú": "u", "ù": "u", "ủ": "u", "ũ": "u", "ụ": "u",
        "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "ý": "y", "ỳ": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    }
    normalized = text.lower()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _date_range(check_in: str, check_out: str) -> List[str]:
    start = _parse_date(check_in)
    end = _parse_date(check_out)
    if end <= start:
        raise ValueError("check_out must be after check_in.")
    days = []
    cursor = start
    while cursor < end:
        days.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return days


def _format_money(value: int) -> str:
    return f"{value:,.0f} VND".replace(",", ".")


class VinpearlToolset:
    """
    Local Vinpearl Nha Trang booking toolset.

    The inventory lives in src/data and includes room capacity, nightly prices,
    inclusions, and date-level availability. Confirmation is guarded by explicit
    user intent so a model cannot accidentally finalize a booking.
    """

    def __init__(self, data_path: str = DATA_PATH):
        self.data_path = data_path
        with open(data_path, "r", encoding="utf-8") as file:
            self.inventory = json.load(file)
        self.last_search_results: List[Dict[str, Any]] = []
        self.last_filtered_results: List[Dict[str, Any]] = []
        self.pending_booking: Optional[Dict[str, Any]] = None
        self.confirmed_bookings: List[Dict[str, Any]] = []

    def search_vinpearl_packages(
        self,
        location: str,
        check_in: str,
        check_out: str,
        adults: int,
        children: int,
        include_sold_out: bool = False,
    ) -> str:
        nights = _date_range(check_in, check_out)
        total_guests = adults + children
        results = []

        for resort in self.inventory["resorts"]:
            if _normalize(location) not in _normalize(resort["location"] + " " + resort["name"]):
                continue
            for room in resort["rooms"]:
                if adults > room["capacity_adults"] or children > room["capacity_children"]:
                    continue

                nightly_statuses = [room["status_by_date"].get(day) for day in nights]
                if any(status is None for status in nightly_statuses):
                    continue

                is_sold_out = any(status["available"] <= 0 or status["status"] == "sold_out" for status in nightly_statuses)
                if is_sold_out and not include_sold_out:
                    continue

                total_price = sum(
                    room["weekend_price_per_night"]
                    if _parse_date(day).weekday() >= 4
                    else room["base_price_per_night"]
                    for day in nights
                )
                min_available = min(status["available"] for status in nightly_statuses)
                combined_status = "sold_out" if is_sold_out else ("limited" if min_available <= 1 else "available")
                results.append(
                    {
                        "package_code": room["code"],
                        "resort": resort["name"],
                        "room_name": room["name"],
                        "location": resort["location"],
                        "check_in": check_in,
                        "check_out": check_out,
                        "nights": len(nights),
                        "adults": adults,
                        "children": children,
                        "total_guests": total_guests,
                        "capacity": f"{room['capacity_adults']} adults, {room['capacity_children']} children",
                        "includes": room["includes"],
                        "status": combined_status,
                        "available_rooms": min_available,
                        "total_price": total_price,
                    }
                )

        self.last_search_results = sorted(results, key=lambda item: item["total_price"])
        self.last_filtered_results = []
        if not self.last_search_results:
            return "Khong tim thay phong/combo phu hop voi ngay, dia diem va so khach."
        return self._format_package_list(self.last_search_results, "Cac lua chon phu hop")

    def filter_packages(self, includes: List[str], max_price: Optional[int] = None) -> str:
        source = self.last_search_results
        required_terms = [_normalize(item) for item in includes]
        results = []
        for package in source:
            included_text = _normalize(" ".join(package["includes"]))
            if all(term in included_text for term in required_terms):
                if max_price is None or package["total_price"] <= max_price:
                    results.append(package)

        self.last_filtered_results = results
        if not results:
            return "Khong co lua chon nao dap ung tat ca tieu chi bat buoc."
        return self._format_package_list(results, "Lua chon sau khi loc")

    def prepare_booking(
        self,
        package_code: str,
        guest_name: str,
        phone: str = "",
        note: str = "",
    ) -> str:
        package = self._find_package(package_code)
        if not package:
            return f"Khong tim thay package_code {package_code} trong ket qua tim kiem gan nhat."
        availability = self._get_current_availability(package)
        if availability["status"] == "sold_out" or availability["available_rooms"] <= 0:
            return f"{package_code} da het phong, khong the tao yeu cau giu cho."
        package["status"] = availability["status"]
        package["available_rooms"] = availability["available_rooms"]

        booking_id = f"VP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.pending_booking = {
            "booking_id": booking_id,
            "status": "pending_confirmation",
            "guest_name": guest_name,
            "phone": phone,
            "note": note,
            "package": package,
        }
        return (
            f"Da tao booking tam {booking_id} cho {guest_name}: "
            f"{package['room_name']} tai {package['resort']}, {package['nights']} dem, "
            f"tong gia {_format_money(package['total_price'])}. "
            "Chua xac nhan dat. Hay hoi lai khach co muon xac nhan dat khong."
        )

    def confirm_booking(self, booking_id: str, user_message: str) -> str:
        if not self.pending_booking or self.pending_booking["booking_id"] != booking_id:
            return f"Khong co booking tam {booking_id} dang cho xac nhan."

        normalized_message = _normalize(user_message)
        if not any(keyword in normalized_message for keyword in CONFIRM_KEYWORDS):
            return (
                "Khong xac nhan booking vi nguoi dung chua noi ro y dinh xac nhan dat. "
                "Chi goi tool nay khi nguoi dung noi ro: xac nhan dat, dong y dat, chot dat."
            )

        booking = self.pending_booking
        availability = self._get_current_availability(booking["package"])
        if availability["status"] == "sold_out" or availability["available_rooms"] <= 0:
            return (
                f"{booking['package']['package_code']} da het phong trong thoi gian "
                f"{booking['package']['check_in']} den {booking['package']['check_out']}. "
                "Booking tam chua duoc xac nhan."
            )

        self._decrement_inventory(booking["package"])
        booking["status"] = "confirmed"
        booking["confirmed_at"] = datetime.now().isoformat(timespec="seconds")
        booking["package"]["available_rooms_after_booking"] = availability["available_rooms"] - 1
        self.confirmed_bookings.append(booking)
        self.pending_booking = None
        package = booking["package"]
        return (
            f"Xac nhan thanh cong booking {booking['booking_id']} cho {booking['guest_name']}. "
            f"Phong: {package['room_name']} - {package['resort']}. "
            f"Ngay: {package['check_in']} den {package['check_out']}. "
            f"Tong gia tam tinh: {_format_money(package['total_price'])}."
        )

    def generate_itinerary(
        self,
        duration_days: int,
        location: str,
        key_activities: List[str],
    ) -> str:
        activity_text = _normalize(" ".join(key_activities))
        vinwonders = "VinWonders" if "vinwonders" in activity_text else "cac tien ich resort"
        show = "19:30 xem Tata Show" if "tata" in activity_text else "buoi toi thu gian tai resort"
        if duration_days <= 1:
            return f"Ngay 1: Den {location}, nhan phong, trai nghiem {vinwonders}, tra phong theo lich."
        if duration_days == 2:
            return (
                f"Ngay 1: Nhan phong tai {location}, nghi ngoi va dung bua toi.\n"
                f"Ngay 2: Trai nghiem {vinwonders}, {show}, sau do tra phong."
            )
        return (
            f"Ngay 1: Nhan phong tai {location} luc 14:00, nghi ngoi, dung bua toi tai resort.\n"
            f"Ngay 2: Danh tron ngay cho {vinwonders}, {show}, quay ve resort nghi ngoi.\n"
            "Ngay 3: An sang, thu gian tai bai bien/hồ boi, 12:00 lam thu tuc tra phong."
        )

    def get_inventory_snapshot(self) -> List[Dict[str, Any]]:
        rows = []
        for resort in self.inventory["resorts"]:
            for room in resort["rooms"]:
                rows.append(
                    {
                        "resort": resort["name"],
                        "code": room["code"],
                        "room_name": room["name"],
                        "base_price": room["base_price_per_night"],
                        "weekend_price": room["weekend_price_per_night"],
                        "includes": room["includes"],
                        "status_by_date": room["status_by_date"],
                    }
                )
        return rows

    def as_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "search_vinpearl_packages",
                "description": "Tim phong/combo Vinpearl Nha Trang theo ngay, so khach, gia va trang thai phong local.",
                "args": 'location: str, check_in: "YYYY-MM-DD", check_out: "YYYY-MM-DD", adults: int, children: int, include_sold_out: bool=False',
                "func": self.search_vinpearl_packages,
            },
            {
                "name": "filter_packages",
                "description": "Loc ket qua tim kiem theo tien ich bat buoc va gia toi da.",
                "args": "includes: list[str], max_price: int|None=None",
                "func": self.filter_packages,
            },
            {
                "name": "prepare_booking",
                "description": "Tao booking tam cho goi khach chon. Chua phai xac nhan dat.",
                "args": "package_code: str, guest_name: str, phone: str='', note: str=''",
                "func": self.prepare_booking,
            },
            {
                "name": "confirm_booking",
                "description": "Chi xac nhan booking khi nguoi dung noi ro muon xac nhan dat/chot dat/dong y dat.",
                "args": "booking_id: str, user_message: str",
                "func": self.confirm_booking,
            },
            {
                "name": "generate_itinerary",
                "description": "Tao lich trinh goi y theo so ngay, resort va hoat dong chinh.",
                "args": "duration_days: int, location: str, key_activities: list[str]",
                "func": self.generate_itinerary,
            },
        ]

    def _find_package(self, package_code: str) -> Optional[Dict[str, Any]]:
        source = self.last_filtered_results or self.last_search_results
        normalized_code = _normalize(package_code)
        for package in source:
            if _normalize(package["package_code"]) == normalized_code:
                return package
        return None

    def _find_room(self, package_code: str) -> Optional[Dict[str, Any]]:
        normalized_code = _normalize(package_code)
        for resort in self.inventory["resorts"]:
            for room in resort["rooms"]:
                if _normalize(room["code"]) == normalized_code:
                    return room
        return None

    def _get_current_availability(self, package: Dict[str, Any]) -> Dict[str, Any]:
        room = self._find_room(package["package_code"])
        if not room:
            return {"status": "sold_out", "available_rooms": 0}

        nights = _date_range(package["check_in"], package["check_out"])
        nightly_statuses = [room["status_by_date"].get(day) for day in nights]
        if any(status is None for status in nightly_statuses):
            return {"status": "sold_out", "available_rooms": 0}

        min_available = min(status["available"] for status in nightly_statuses)
        is_sold_out = any(
            status["available"] <= 0 or status["status"] == "sold_out"
            for status in nightly_statuses
        )
        combined_status = "sold_out" if is_sold_out else ("limited" if min_available <= 1 else "available")
        return {"status": combined_status, "available_rooms": min_available}

    def _decrement_inventory(self, package: Dict[str, Any]) -> None:
        room = self._find_room(package["package_code"])
        if not room:
            raise ValueError(f"Cannot update inventory for {package['package_code']}.")

        for day in _date_range(package["check_in"], package["check_out"]):
            status = room["status_by_date"][day]
            if status["available"] <= 0:
                raise ValueError(f"{package['package_code']} da het phong ngay {day}.")
            status["available"] -= 1
            if status["available"] <= 0:
                status["status"] = "sold_out"
            elif status["available"] == 1:
                status["status"] = "limited"
            else:
                status["status"] = "available"

        self._persist_inventory()

    def _persist_inventory(self) -> None:
        with open(self.data_path, "w", encoding="utf-8") as file:
            json.dump(self.inventory, file, ensure_ascii=False, indent=2)
            file.write("\n")

    def _format_package_list(self, packages: List[Dict[str, Any]], title: str) -> str:
        lines = [f"{title}:"]
        for package in packages:
            includes = " + ".join(package["includes"])
            lines.append(
                "- {code}: {room} tai {resort} | {nights} dem | {status}, con {available} phong | "
                "{price} | Bao gom: {includes} | Suc chua: {capacity}".format(
                    code=package["package_code"],
                    room=package["room_name"],
                    resort=package["resort"],
                    nights=package["nights"],
                    status=package["status"],
                    available=package["available_rooms"],
                    price=_format_money(package["total_price"]),
                    includes=includes,
                    capacity=package["capacity"],
                )
            )
        return "\n".join(lines)


def build_vinpearl_tools(toolset: Optional[VinpearlToolset] = None) -> List[Dict[str, Any]]:
    return (toolset or VinpearlToolset()).as_tools()
