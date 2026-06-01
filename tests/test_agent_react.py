import os
import sys
import unittest
from typing import Optional, Dict, Any

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.vinpearl_tools import search_rooms, search_nearby_attractions, filter_packages
from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider

class MockLLMProvider(LLMProvider):
    def __init__(self, responses: list):
        super().__init__(model_name="mock-model")
        self.responses = responses
        self.call_count = 0

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if self.call_count >= len(self.responses):
            resp = "Final Answer: Error - Mock ran out of responses."
        else:
            resp = self.responses[self.call_count]
        self.call_count += 1
        return {
            "content": resp,
            "usage": {"prompt_tokens": 50, "completion_tokens": 50, "total_tokens": 100},
            "latency_ms": 120,
            "provider": "mock"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        pass

class TestVinpearlAgent(unittest.TestCase):
    
    def test_search_rooms_availability(self):
        # 2026-06-05 and 2026-06-06 are blocked for PKG-A
        res_blocked = search_rooms("Nha Trang", "2026-06-05", "2026-06-07", 2)
        # Should NOT contain PKG-A
        pkg_ids = [p["id"] for p in res_blocked if "id" in p]
        self.assertNotIn("PKG-A", pkg_ids)
        
        # PKG-B is available
        self.assertIn("PKG-B", pkg_ids)
        
        # Checking date 2026-06-07 to 2026-06-08 (no blocked dates for PKG-A)
        res_avail = search_rooms("Nha Trang", "2026-06-07", "2026-06-09", 2)
        pkg_ids_avail = [p["id"] for p in res_avail if "id" in p]
        self.assertIn("PKG-A", pkg_ids_avail)

    def test_search_rooms_capacity(self):
        # Check capacity constraint (guests = 8 is too large for PKG-A/B which have max_adults=2, max_children=1)
        res_large = search_rooms("Nha Trang", "2026-06-07", "2026-06-09", 8)
        pkg_ids = [p["id"] for p in res_large if "id" in p]
        self.assertNotIn("PKG-A", pkg_ids)
        self.assertNotIn("PKG-B", pkg_ids)
        
        # PKG-C has max_adults=6, max_children=3 -> total capacity 9, should fit 8 guests
        self.assertIn("PKG-C", pkg_ids)

    def test_search_nearby_attractions_fuzzy(self):
        # Vietnamese "ca nhạc" or "show" should map to show types (ATTR-A: VinWonders Nha Trang, ATTR-D: Tata Show)
        res_show = search_nearby_attractions("Nha Trang", "ca nhạc")
        names = [a["name"] for a in res_show]
        self.assertIn("VinWonders Nha Trang", names)
        self.assertIn("Tata Show", names)

        # Vietnamese "trị liệu" or "spa" should map to spa types (ATTR-B: Akoya Spa, ATTR-E: Imperial Club Spa)
        res_spa = search_nearby_attractions("Nha Trang", "trị liệu")
        names_spa = [a["name"] for a in res_spa]
        self.assertIn("Akoya Spa", names_spa)
        self.assertIn("Imperial Club Spa", names_spa)

    def test_filter_packages(self):
        packages = [
            {"id": "PKG-A", "includes": ["Room Only", "Private Beach Access"]},
            {"id": "PKG-C", "includes": ["Breakfast", "VinWonders", "Private Pool"]}
        ]
        
        # Filter by VinWonders
        res = filter_packages(packages, ["VinWonders"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], "PKG-C")

    def test_agent_react_loop_and_ast_parsing(self):
        # Mocking the sequence of outputs from the LLM
        mock_responses = [
            # Step 1: Search rooms
            'Thought: Tôi cần tìm phòng trống ở Nha Trang.\nAction: search_rooms(location="Nha Trang", checkin="2026-06-07", checkout="2026-06-09", guests=2)',
            # Step 2: Filter packages with complex structure arguments
            'Thought: Có các phòng này. Giờ tôi cần lọc phòng có Spa Voucher.\nAction: filter_packages(packages=[{"id": "PKG-D", "hotel": "Vinpearl Luxury Nha Trang", "includes": ["Breakfast", "Airport Shuttle", "Spa Voucher"]}], includes=["Spa Voucher"])',
            # Step 3: Final Answer
            'Thought: Đã lọc thành công phòng PKG-D. Tôi sẽ trả lời khách hàng.\nFinal Answer: Có phòng Grand Deluxe Room Garden View tại Vinpearl Luxury Nha Trang trống từ 2026-06-07 đến 2026-06-09 với tiện ích Spa Voucher đi kèm.'
        ]
        
        mock_llm = MockLLMProvider(mock_responses)
        tools = [
            {"name": "search_rooms", "description": "Search rooms"},
            {"name": "search_nearby_attractions", "description": "Search attractions"},
            {"name": "filter_packages", "description": "Filter packages"}
        ]
        
        agent = ReActAgent(mock_llm, tools, max_steps=5)
        response = agent.run("Tìm phòng có Spa tại Nha Trang từ 7/6 đến 9/6 cho 2 người.")
        
        self.assertIn("Vinpearl Luxury Nha Trang", response)
        self.assertIn("Grand Deluxe Room Garden View", response)
        
        # Verify call history and AST parsing
        self.assertEqual(mock_llm.call_count, 3)
        self.assertTrue(any("Observation:" in h for h in agent.history))

if __name__ == "__main__":
    unittest.main()
