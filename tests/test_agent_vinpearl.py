import os
import sys
from dotenv import load_dotenv

# Add root folder to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.llm_provider import LLMProvider
from src.agent.agent import ReActAgent
from src.tools.vinpearl_tools import (
    search_rooms,
    search_nearby_attractions,
    search_vinpearl_packages,
    filter_packages,
    generate_itinerary
)

def test_vinpearl_react_agent():
    load_dotenv()
    
    # Initialize provider based on environment config
    provider_name = os.getenv("DEFAULT_PROVIDER", "google").lower()
    model_name = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
    
    print("="*60)
    print(f"🧪 CHẠY KIỂM THỬ REACT AGENT VỚI PROVIDER: {provider_name.upper()}")
    print(f"🤖 Model: {model_name}")
    print("="*60)
    
    if provider_name == "google":
        from src.core.gemini_provider import GeminiProvider
        provider = GeminiProvider(model_name=model_name)
    elif provider_name == "openai":
        from src.core.openai_provider import OpenAIProvider
        provider = OpenAIProvider(model_name=model_name)
    else:
        from src.core.local_provider import LocalProvider
        provider = LocalProvider(model_path=os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf"))
        
    # Setup tools list
    tools = [
        {
            "name": "search_rooms",
            "description": "search_rooms(location: str, min_price: float, max_price: float, check_in: str, check_out: str, adults: int, children: int) -> Trả về các gói phòng phù hợp ngân sách và sức chứa.",
            "func": search_rooms
        },
        {
            "name": "search_nearby_attractions",
            "description": "search_nearby_attractions(location: str, attraction_type: str) -> Trả về danh sách địa điểm ẩm thực, giải trí, spa xung quanh Nha Trang.",
            "func": search_nearby_attractions
        },
        {
            "name": "search_vinpearl_packages",
            "description": "search_vinpearl_packages(location: str, check_in: str, check_out: str, adults: int, children: int) -> Trả về các gói combo nghỉ dưỡng Vinpearl Nha Trang phù hợp số lượng khách.",
            "func": search_vinpearl_packages
        },
        {
            "name": "filter_packages",
            "description": "filter_packages(packages: List[dict], includes: List[str]) -> Lọc danh sách combo theo các tiện ích bắt buộc phải có (ví dụ: ['VinWonders']). Yêu cầu đối số 'packages' phải là kết quả trả về từ hàm search_vinpearl_packages.",
            "func": filter_packages
        },
        {
            "name": "generate_itinerary",
            "description": "generate_itinerary(duration_days: int, location: str, key_activities: List[str]) -> Sinh lịch trình vui chơi chi tiết theo từng ngày (ví dụ: duration_days=3, key_activities=['VinWonders', 'Tata Show']).",
            "func": generate_itinerary
        }
    ]
    
    agent = ReActAgent(llm=provider, tools=tools, max_steps=6)
    
    # Test Scenario
    user_query = (
        "Tìm và đặt combo nghỉ dưỡng Vinpearl Nha Trang 3 ngày 2 đêm cho gia đình 4 người "
        "(2 người lớn, 2 trẻ em) vào cuối tuần tới, có bao gồm vé vui chơi VinWonders. "
        "Hãy thiết kế lịch trình mẫu dựa trên combo tìm được và các điểm giải trí nổi bật xung quanh!"
    )
    
    print(f"\nUser Request:\n{user_query}\n")
    print("..." * 20)
    print("Đang khởi chạy ReAct Loop...\n")
    
    result = agent.run(user_query)
    
    print("\n" + "="*50)
    print("📈 KẾT QUẢ SUY LUẬN BẰNG REACT LOOP")
    print("="*50)
    
    for step in result["steps"]:
        print(f"\n[BƯỚC {step['step']}]")
        print(f"🧠 Thought: {step['thought']}")
        if step.get("action"):
            print(f"🛠️ Action: {step['action']}")
        if step.get("observation"):
            print(f"👁️ Observation:\n{step['observation'][:500]}...")
            
    print("\n" + "="*50)
    print("💬 FINAL ANSWER (CÂU TRẢ LỜI CUỐI CÙNG)")
    print("="*50)
    print(result["answer"])
    print("="*60)
    print("✅ Kiểm thử hoàn thành thành công!")

if __name__ == "__main__":
    test_vinpearl_react_agent()
