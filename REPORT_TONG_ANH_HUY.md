# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Tống Anh Huy
- **Student ID**: 2A202600761
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Mô tả đóng góp cụ thể của bạn đối với codebase (ví dụ: phát triển các công cụ nghiệp vụ, tối ưu bộ phân tích cú pháp tham số phức tạp).*

- **Modules Implemented**: [vinpearl_tools.py](file:///c:/code/VinUni/Day-3-Lab-Chatbot-vs-react-agent/src/tools/vinpearl_tools.py) (Hàm `search_rooms`, `search_nearby_attractions` với Fuzzy Keyword mapping, `filter_packages`), và tối ưu hóa hàm `_parse_action` trong [agent.py](file:///c:/code/VinUni/Day-3-Lab-Chatbot-vs-react-agent/src/agent/agent.py) bằng Abstract Syntax Tree.
- **Code Highlights**:
  ```python
  # Ánh xạ từ khóa tiếng Việt thông dụng sang nhãn cơ sở dữ liệu (Fuzzy Semantic Matching)
  elif "show" in req_type_lower or "diễn" in req_type_lower or "ca nhạc" in req_type_lower:
      if "show" in attr_type_lower or "show" in attr_name_lower:
          is_match = True
  elif "spa" in req_type_lower or "trị liệu" in req_type_lower or "tắm" in req_type_lower:
      if "spa" in attr_type_lower or "spa" in attr_name_lower:
          is_match = True
  ```
  ```python
  # Biên dịch tham số cấu trúc phức tạp bằng Abstract Syntax Tree (AST)
  tree = ast.parse(f"dummy({args_str})")
  call_node = tree.body[0].value
  args = {}
  for kw in call_node.keywords:
      args[kw.arg] = ast.literal_eval(kw.value)
  ```
- **Documentation**: 
  Tôi chịu trách nhiệm phát triển toàn bộ các công cụ (tools) nghiệp vụ của hệ thống, tương tác với cơ sở dữ liệu `packages.json` và `attractions.json`. Tôi đã thiết kế bộ lọc so khớp phòng trống dựa trên danh sách các ngày bận (`blocked_dates`), xây dựng cơ chế ánh xạ từ khóa thông minh (Fuzzy Matching) để nhận diện các yêu cầu tiếng Việt của khách hàng thành nhãn cơ sở dữ liệu tương ứng. Đồng thời, tôi đã nâng cấp bộ biên dịch tham số của Agent bằng AST để giải quyết triệt để lỗi phân tích các kiểu dữ liệu phức tạp.

---

## II. Debugging Case Study (10 Points)

*Phân tích một sự cố cụ thể mà bạn gặp phải trong quá trình làm lab thông qua hệ thống log.*

- **Problem Description**: Lỗi thực thi công cụ `filter_packages` khi Agent muốn lọc tiện ích của các gói phòng nhận được từ bước trước: `Lỗi khi thực thi công cụ filter_packages: 'str' object has no attribute 'get'`.
- **Log Source**: `logs/2026-06-01.log`
  ```json
  {"timestamp": "2026-06-01T09:42:08.888443", "event": "TOOL_EXECUTION_START", "data": {"tool": "filter_packages", "args": {"packages": ["id", "PKG-A", "name", "Deluxe Room Ocean View (Room Only)", "hotel", "Vinpearl Resort Nha Trang", "location", "Nha Trang", "room_type", "Deluxe Room Ocean View", "price_per_night", "max_adults", "max_children", "includes", "Room Only", "Private Beach Access", "Swimming Pool"], "includes": ["VinWonders"]}}}
  {"timestamp": "2026-06-01T09:42:08.889153", "event": "TOOL_EXECUTION_END", "data": {"error": "Lỗi khi thực thi công cụ filter_packages: 'str' object has no attribute 'get'"}}
  ```
- **Diagnosis**: Bộ bóc tách tham số cũ dựa trên Regex đã cố tình tách mảng bằng cách split dấu phẩy `,`. Điều này khiến danh sách các Dictionary phức tạp bị phá vỡ cấu trúc và biến thành một mảng phẳng các chuỗi ký tự thô. Khi truyền vào `filter_packages` để thực hiện vòng lặp đọc tiện ích (`pkg.get("includes")`), chương trình bị crash do chuỗi ký tự không hỗ trợ hàm `.get()`.
- **Solution**: Tôi đã loại bỏ hoàn toàn cơ chế Regex cũ và thay thế bằng module `ast`. Bằng cách wrap chuỗi đối số và parse qua `ast.parse` kết hợp `ast.literal_eval`, Python biên dịch trực tiếp và chính xác kiểu dữ liệu lồng nhau (như danh sách các Dictionaries), giúp tham số truyền vào công cụ bảo toàn 100% cấu trúc ban đầu.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Phản ánh sự khác biệt về năng lực lập luận giữa Chatbot truyền thống và ReAct Agent.*

1. **Reasoning**: Thought đóng vai trò cực kỳ quan trọng trong việc định hình các bước gọi công cụ của Agent. Nó giúp mô hình lập luận logic: đầu tiên phải dùng `search_rooms` để có danh sách phòng, sau đó mới dùng `filter_packages` để lọc, rồi dùng `generate_itinerary` để lên lịch. Chatbot truyền thống hoàn toàn thiếu khả năng lập kế hoạch tuần tự này.
2. **Reliability**: ReAct Agent có độ chính xác tuyệt đối nhờ truy vấn dữ liệu từ DB thực tế. Chatbot thông thường rất dễ bị "bịa đặt" thông tin (hallucination) để làm hài lòng người dùng, điều này cực kỳ nguy hiểm trong nghiệp vụ khách sạn (giá phòng ảo, ngày hết phòng vẫn đặt được).
3. **Observation**: Observation phản hồi chính xác kết quả từ cơ sở dữ liệu giúp mô hình có thông tin thực tế để điều chỉnh suy luận ở bước tiếp theo, tránh bị phiến diện.

---

## IV. Future Improvements (5 Points)

*Cách bạn sẽ mở rộng hệ thống này cho một môi trường AI Agent thực tế lớn.*

- **Scalability**: Thiết kế cơ chế lưu trữ đệm (caching) bằng Redis cho các cuộc gọi công cụ tĩnh ít thay đổi (như tìm kiếm địa điểm vui chơi giải trí xung quanh), giúp nâng cao hiệu năng hệ thống lên gấp 10 lần.
- **Safety**: Xây dựng bộ Schema Validation chặt chẽ bằng thư viện Pydantic cho đầu vào của tất cả các công cụ, đảm bảo kiểu dữ liệu luôn an toàn trước khi chạy mã nghiệp vụ lõi.
- **Performance**: Chuyển đổi dữ liệu JSON tĩnh sang cơ sở dữ liệu quan hệ (PostgreSQL) hoặc NoSQL để xử lý hàng triệu gói phòng nghỉ và lịch trống một cách hiệu quả và song song.
