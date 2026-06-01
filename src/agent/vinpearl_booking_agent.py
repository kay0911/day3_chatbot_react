import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider
from src.tools.vinpearl_tools import CONFIRM_KEYWORDS, VinpearlToolset, _normalize, _format_money


def _is_pure_greeting(text: str) -> bool:
    normalized = _normalize(text).strip()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    greetings = ["chao", "hello", "hi", "helo", "xin chao", "chao ban", "chao ad", "chao bot", "chao assistant"]
    if normalized in greetings:
        return True
    words = normalized.split()
    if len(words) <= 2 and any(g in words for g in ["chao", "hello", "hi", "helo", "xin"]):
        # Check that it doesn't contain important booking keywords
        booking_keywords = ["phong", "dat", "book", "tim", "gia", "combo"]
        if not any(k in normalized for k in booking_keywords):
            return True
    return False


def _is_relevant(text: str, pending_booking: bool = False) -> bool:
    normalized = _normalize(text).strip()
    # Replace punctuation with spaces
    cleaned = re.sub(r"[^\w\s]", " ", normalized)
    words = set(cleaned.split())
    
    # 1. Package code check (e.g. FAM-SUITE-VW)
    package_codes = re.findall(r"\b([A-Z0-9]+(?:-[A-Z0-9]+)+)\b", text.upper())
    if package_codes:
        return True
        
    # 2. Price pattern check (e.g. 28.400.000, 28,400,000, 28400000, 5 trieu, etc.)
    if re.search(r"\b\d[\d.,]{5,}\b", normalized) or "trieu" in normalized or "million" in normalized:
        return True
        
    # 3. Confirmation check if there is a pending booking
    if pending_booking:
        confirmations = ["xac nhan", "dong y", "chot", "confirm", "ok", "oke", "yep", "yes", "dung vay", "chinh xac"]
        if any(keyword in normalized for keyword in confirmations):
            return True
            
    # 4. Relevant single-word keywords (must match exactly as a full word)
    single_word_keywords = {
        "phong", "dat", "book", "tim", "gia", "tien", "combo", "goi",
        "package", "villa", "suite", "deluxe", "resort", "hotel",
        "ngay", "dem", "khach", "confirm", "ok", "oke", "yep", "yes",
        "tata", "buffet", "vnd"
    }
    
    if any(keyword in words for keyword in single_word_keywords):
        return True
        
    # 5. Relevant multi-word phrases (must match as a substring with word boundaries)
    multi_word_phrases = [
        "check in", "check_in", "check out", "check_out", 
        "nguoi lon", "tre em", "khach san", "vinwonders", "vin wonders",
        "vui choi", "an sang", "an ba bua", "chi phi", "tra cuu", "kiem tra"
    ]
    
    for phrase in multi_word_phrases:
        if phrase in normalized:
            pattern = rf"\b{re.escape(phrase)}\b"
            if re.search(pattern, normalized):
                return True
                
    # 6. Specific price question context (e.g. contains "bao nhieu" and at least one other booking word)
    if "bao nhieu" in normalized:
        pattern = r"\bbao nhieu\b"
        if re.search(pattern, normalized):
            query_context = ["phong", "gia", "combo", "goi", "resort", "villa", "suite", "deluxe", "ve", "booking", "tien", "chi phi"]
            if any(context_word in words for context_word in query_context):
                return True
                
    return False


def _extract_specific_price(text: str) -> Optional[int]:
    normalized = _normalize(text)
    million_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:trieu|million)", normalized)
    if million_match:
        val = float(million_match.group(1).replace(",", "."))
        return int(val * 1_000_000)

    money_match = re.search(r"(\d[\d.,]{5,})\s*(?:vnd|dong|d)?", normalized)
    if money_match:
        digits = re.sub(r"\D", "", money_match.group(1))
        return int(digits) if digits else None
    return None


def _describe_room_package(package: Dict[str, Any]) -> str:
    code = package.get("package_code") or package.get("code")
    name = package.get("room_name") or package.get("name")
    resort = package.get("resort") or ""
    includes = " + ".join(package.get("includes", []))
    
    price_str = ""
    if "total_price" in package:
        price_str = f"tổng giá {_format_money(package['total_price'])}"
    else:
        base_p = package.get("base_price_per_night") or package.get("base_price") or 0
        weekend_p = package.get("weekend_price_per_night") or package.get("weekend_price") or 0
        price_str = f"giá từ {_format_money(base_p)}/đêm (cuối tuần {_format_money(weekend_p)}/đêm)"
        
    capacity = package.get("capacity") or f"{package.get('capacity_adults', 2)} người lớn, {package.get('capacity_children', 0)} trẻ em"
    capacity = capacity.replace("adults", "người lớn").replace("children", "trẻ em")
    
    resort_str = f" tại {resort}" if resort else ""
    
    return f"Gói {code}: {name}{resort_str} | {price_str} | Bao gồm: {includes} | Sức chứa: {capacity}."


class RuleBasedVinpearlAgent:
    """
    Deterministic fallback for the chatbot UI when the local GGUF model is not
    available yet. It uses the same local tools and keeps the confirmation guard.
    """

    def __init__(self, toolset: VinpearlToolset):
        self.toolset = toolset
        self.history: List[Dict[str, str]] = []

    def _handle_lookup(self, user_input: str) -> Optional[str]:
        # 1. Check for package code
        package_code = self._extract_package_code(user_input)
        if package_code:
            # Find in last search/filtered results
            package = self.toolset._find_package(package_code)
            if package:
                return f"Thông tin về gói {package_code}:\n{_describe_room_package(package)}"
            # Find in all inventory rooms
            room = self.toolset._find_room(package_code)
            if room:
                resort_name = ""
                for resort in self.toolset.inventory["resorts"]:
                    if any(r["code"] == room["code"] for r in resort["rooms"]):
                        resort_name = resort["name"]
                        break
                room_copy = dict(room)
                room_copy["resort"] = resort_name
                return f"Thông tin về gói {package_code}:\n{_describe_room_package(room_copy)}"
                
        # 2. Check for price
        price = _extract_specific_price(user_input)
        if price is not None:
            # Find in last search/filtered results matching total_price
            for pkg in (self.toolset.last_filtered_results or self.toolset.last_search_results):
                if pkg.get("total_price") == price:
                    return f"Phòng có giá {_format_money(price)} trong danh sách lựa chọn phù hợp gần nhất là:\n{_describe_room_package(pkg)}"
            # Find in inventory matching base_price or weekend_price
            for resort in self.toolset.inventory["resorts"]:
                for room in resort["rooms"]:
                    if room.get("base_price_per_night") == price or room.get("weekend_price_per_night") == price:
                        room_copy = dict(room)
                        room_copy["resort"] = resort["name"]
                        return f"Phòng có giá {_format_money(price)} trong hệ thống là:\n{_describe_room_package(room_copy)}"
                        
        return None

    def run(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})
        normalized = _normalize(user_input)

        # 1. Check for greeting first
        if _is_pure_greeting(user_input):
            answer = "Chào bạn! Tôi là trợ lý ảo chuyên hỗ trợ tìm phòng và đặt phòng tại Vinpearl Nha Trang. Bạn cần hỗ trợ tìm phòng hay đặt phòng cho thời gian nào ạ?"
            self.history.append({"role": "assistant", "content": answer})
            return answer

        # 2. Check for specific lookup query
        lookup_answer = self._handle_lookup(user_input)
        if lookup_answer:
            self.history.append({"role": "assistant", "content": lookup_answer})
            return lookup_answer

        # 3. Check for relevance
        has_pending = self.toolset.pending_booking is not None
        if not _is_relevant(user_input, pending_booking=has_pending):
            answer = "Xin lỗi, tôi là trợ lý ảo chuyên hỗ trợ tìm phòng và đặt phòng tại Vinpearl Nha Trang. Tôi không thể trả lời các câu hỏi ngoài phạm vi này."
            self.history.append({"role": "assistant", "content": answer})
            return answer

        # 4. Proceed with original flow
        if self._has_confirmation(normalized) and self.toolset.pending_booking:
            pending_id = self.toolset.pending_booking["booking_id"]
            answer = self.toolset.confirm_booking(pending_id, user_input)
            self.history.append({"role": "assistant", "content": answer})
            return answer

        package_code = self._extract_package_code(user_input)
        if package_code and any(word in normalized for word in ["giu cho", "tao booking", "dat tam", "dat phong"]):
            guest_name = self._extract_guest_name(user_input) or "Khach Vinpearl"
            answer = self.toolset.prepare_booking(package_code=package_code, guest_name=guest_name)
            self.history.append({"role": "assistant", "content": answer})
            return answer

        search_params = self._extract_search_params(user_input)
        observation = self.toolset.search_vinpearl_packages(**search_params)
        max_price = self._extract_max_price(user_input)
        includes = ["VinWonders"] if "vinwonders" in normalized else []
        if includes or max_price is not None:
            observation = self.toolset.filter_packages(includes=includes, max_price=max_price)

        nights = self._nights(search_params["check_in"], search_params["check_out"])
        itinerary = self.toolset.generate_itinerary(
            duration_days=nights + 1,
            location="Vinpearl Nha Trang",
            key_activities=["VinWonders", "Tata Show"] if "vinwonders" in normalized else ["Resort Relaxing"],
        )
        answer = (
            f"{observation}\n\n"
            f"Lich trinh goi y:\n{itinerary}\n\n"
            "Neu muon giu cho, hay nhan: dat tam <ma goi> cho <ten khach>. "
            "Toi chi xac nhan dat khi ban noi ro 'xac nhan dat' hoac 'chot dat'."
        )
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def _extract_search_params(self, text: str) -> Dict[str, Any]:
        dates = self._extract_dates(text)
        if len(dates) >= 2:
            check_in, check_out = dates[0], dates[1]
        elif len(dates) == 1:
            check_in_date = date.fromisoformat(dates[0])
            check_in = check_in_date.isoformat()
            check_out = (check_in_date + timedelta(days=1)).isoformat()
        else:
            today = date.today()
            days_until_friday = (4 - today.weekday()) % 7 or 7
            check_in_date = today + timedelta(days=days_until_friday)
            check_in = check_in_date.isoformat()
            check_out = (check_in_date + timedelta(days=2)).isoformat()

        adults = self._extract_count(text, ["nguoi lon", "adult", "adults"]) or 2
        children = self._extract_count(text, ["tre em", "tre", "child", "children"]) or 0
        return {
            "location": "Nha Trang",
            "check_in": check_in,
            "check_out": check_out,
            "adults": adults,
            "children": children,
        }

    def _extract_dates(self, text: str) -> List[str]:
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", text)
        for day, month, year in re.findall(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text):
            parsed = date(int(year), int(month), int(day)).isoformat()
            if parsed not in dates:
                dates.append(parsed)
        return dates

    def _extract_max_price(self, text: str) -> Optional[int]:
        normalized = _normalize(text)
        if not any(keyword in normalized for keyword in ["duoi", "toi da", "khong qua", "<=", "nho hon"]):
            return None

        million_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:trieu|million)", normalized)
        if million_match:
            return int(float(million_match.group(1).replace(",", ".")) * 1_000_000)

        money_match = re.search(r"(\d[\d.,]{5,})\s*(?:vnd|dong|d)?", normalized)
        if money_match:
            digits = re.sub(r"\D", "", money_match.group(1))
            return int(digits) if digits else None
        return None

    def _extract_count(self, text: str, labels: List[str]) -> Optional[int]:
        normalized = _normalize(text)
        for label in labels:
            match = re.search(rf"(\d+)\s*{re.escape(_normalize(label))}", normalized)
            if match:
                return int(match.group(1))
        return None

    def _extract_package_code(self, text: str) -> Optional[str]:
        matches = re.findall(r"\b([A-Z0-9]+(?:-[A-Z0-9]+)+)\b", text.upper())
        return matches[0] if matches else None

    def _extract_guest_name(self, text: str) -> Optional[str]:
        match = re.search(r"\bcho\s+(.+)$", text, re.IGNORECASE)
        if not match:
            return None
        name = match.group(1).strip()
        return name if name else None

    def _has_confirmation(self, normalized: str) -> bool:
        return any(keyword in normalized for keyword in CONFIRM_KEYWORDS)

    def _nights(self, check_in: str, check_out: str) -> int:
        start = date.fromisoformat(check_in)
        end = date.fromisoformat(check_out)
        return max((end - start).days, 1)


class VinpearlChatAgent:
    """
    Chat wrapper that uses LocalProvider/ReAct when a model is present, with a
    deterministic fallback for development and UI testing.
    """

    def __init__(self, toolset: VinpearlToolset, llm: Optional[LLMProvider] = None):
        self.toolset = toolset
        self.mode = "local-model" if llm else "rule-based"
        self.agent = (
            ReActAgent(llm=llm, tools=toolset.as_tools(), max_steps=6)
            if llm
            else RuleBasedVinpearlAgent(toolset)
        )

    def run(self, user_input: str) -> str:
        # 1. Check for greeting first
        if _is_pure_greeting(user_input):
            return "Chào bạn! Tôi là trợ lý ảo chuyên hỗ trợ tìm phòng và đặt phòng tại Vinpearl Nha Trang. Bạn cần hỗ trợ tìm phòng hay đặt phòng cho thời gian nào ạ?"

        # 2. Check for specific lookup query (price or package code info)
        if isinstance(self.agent, RuleBasedVinpearlAgent):
            lookup_answer = self.agent._handle_lookup(user_input)
            if lookup_answer:
                return lookup_answer
        else:
            temp_rule_agent = RuleBasedVinpearlAgent(self.toolset)
            lookup_answer = temp_rule_agent._handle_lookup(user_input)
            if lookup_answer:
                return lookup_answer

        # 3. Check for relevance
        has_pending = self.toolset.pending_booking is not None
        if not _is_relevant(user_input, pending_booking=has_pending):
            return "Xin lỗi, tôi là trợ lý ảo chuyên hỗ trợ tìm phòng và đặt phòng tại Vinpearl Nha Trang. Tôi không thể trả lời các câu hỏi ngoài phạm vi này."

        return self.agent.run(user_input)
