import os
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import core modules
from src.core.llm_provider import LLMProvider
from src.agent.agent import ReActAgent
from src.tools.vinpearl_tools import (
    search_rooms,
    search_nearby_attractions,
    search_vinpearl_packages,
    filter_packages,
    generate_itinerary
)

# Initialize provider based on .env
def get_provider() -> LLMProvider:
    provider_name = os.getenv("DEFAULT_PROVIDER", "google").lower()
    model_name = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
    
    print(f"Initializing LLM Provider: {provider_name} with model: {model_name}")
    
    if provider_name == "google":
        from src.core.gemini_provider import GeminiProvider
        return GeminiProvider(model_name=model_name)
    elif provider_name == "openai":
        from src.core.openai_provider import OpenAIProvider
        # Fallback if key not loaded
        api_key = os.getenv("OPENAI_API_KEY")
        return OpenAIProvider(model_name=model_name, api_key=api_key)
    elif provider_name == "local":
        from src.core.local_provider import LocalProvider
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        return LocalProvider(model_path=model_path)
    else:
        raise ValueError(f"Unknown provider: {provider_name}")

# Tools dictionary for ReAct Agent
agent_tools = [
    {
        "name": "search_rooms",
        "description": "search_rooms(location: str, min_price: float, max_price: float, check_in: str, check_out: str, adults: int, children: int) -> Trả về danh sách phòng/villa trong khoảng giá từ min_price tới max_price và có sức chứa phù hợp.",
        "func": search_rooms
    },
    {
        "name": "search_nearby_attractions",
        "description": "search_nearby_attractions(location: str, attraction_type: str) -> Trả về danh sách địa điểm ẩm thực, giải trí, show diễn, spa xung quanh Nha Trang/Hòn Tre.",
        "func": search_nearby_attractions
    },
    {
        "name": "search_vinpearl_packages",
        "description": "search_vinpearl_packages(location: str, check_in: str, check_out: str, adults: int, children: int) -> Trả về danh sách gói combo nghỉ dưỡng Vinpearl Nha Trang phù hợp số người lớn, trẻ em.",
        "func": search_vinpearl_packages
    },
    {
        "name": "filter_packages",
        "description": "filter_packages(packages: List[dict], includes: List[str]) -> Lọc danh sách combo theo các tiện ích bắt buộc phải có (ví dụ: ['VinWonders']). Yêu cầu đối số 'packages' được lấy từ kết quả các hàm tìm kiếm trước đó.",
        "func": filter_packages
    },
    {
        "name": "generate_itinerary",
        "description": "generate_itinerary(duration_days: int, location: str, key_activities: List[str]) -> Sinh lịch trình vui chơi và nghỉ dưỡng theo ngày (ví dụ: duration_days=3, key_activities=['VinWonders', 'Tata Show']).",
        "func": generate_itinerary
    }
]

# Request Handler for Web Server
class VinpearlAgentHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Clean path
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # Default to index.html
        if path == "/":
            path = "/index.html"
            
        # Serve static files from web/ folder
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
        file_path = os.path.join(web_dir, path.lstrip("/"))
        
        # Sanitize path to prevent directory traversal
        if not file_path.startswith(web_dir):
            self.send_error(403, "Access Denied")
            return
            
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            
            # Set correct MIME type
            if file_path.endswith(".html"):
                self.send_header("Content-Type", "text/html; charset=utf-8")
            elif file_path.endswith(".js"):
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
            elif file_path.endswith(".css"):
                self.send_header("Content-Type", "text/css; charset=utf-8")
            elif file_path.endswith(".json"):
                self.send_header("Content-Type", "application/json; charset=utf-8")
            elif file_path.endswith(".png"):
                self.send_header("Content-Type", "image/png")
            elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                self.send_header("Content-Type", "image/jpeg")
            else:
                self.send_header("Content-Type", "application/octet-stream")
                
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # API Chat Endpoint
        if path == "/api/chat":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data)
                user_message = data.get("message", "")
                chat_history = data.get("history", [])
                
                if not user_message:
                    self.send_json_response(400, {"error": "Message is required"})
                    return
                
                # Ghép lịch sử hội thoại trước đó làm ngữ cảnh suy luận (Session Memory)
                full_query = ""
                if chat_history:
                    full_query += "Lịch sử hội thoại trước đó:\n"
                    for msg in chat_history:
                        role_name = "Khách hàng" if msg.get("role") == "user" else "Trợ lý"
                        # Giới hạn nội dung hiển thị trong lịch sử để tránh phình token
                        content_excerpt = msg.get("content", "")
                        full_query += f"- {role_name}: {content_excerpt}\n"
                    full_query += "\n"
                
                full_query += f"Yêu cầu hiện tại của khách hàng: {user_message}"
                
                # Dynamic Provider Fetch (so changes in .env are picked up if server restarted)
                provider = get_provider()
                agent = ReActAgent(llm=provider, tools=agent_tools, max_steps=6)
                
                # Execute agent
                print(f"\n--- Running Agent for Query: '{user_message}' ---")
                response = agent.run(full_query)
                print("--- Agent Execution Completed ---\n")
                
                self.send_json_response(200, response)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json_response(500, {"error": str(e)})
        else:
            self.send_error(404, "API Endpoint Not Found")

    def send_json_response(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # CORS
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def run_server(port=5000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, VinpearlAgentHandler)
    print(f"🚀 Web Server running successfully at http://localhost:{port}")
    print(f"Open your browser and navigate to http://localhost:{port} to interact with the ReAct Chatbot Agent!")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    # Ensure web directory exists
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"), exist_ok=True)
    run_server()
