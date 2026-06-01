# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Trần Duy Khánh
- **Student ID**: 2A202600592
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Mô tả đóng góp cụ thể của bạn đối với codebase (ví dụ: phát triển luồng ReAct lõi, cấu hình LLM Provider, tích lũy Token Telemetry).*

- **Modules Implemented**: [agent.py](file:///c:/code/VinUni/Day-3-Lab-Chatbot-vs-react-agent/src/agent/agent.py) (Hàm `run`), [gemini_provider.py](file:///c:/code/VinUni/Day-3-Lab-Chatbot-vs-react-agent/src/core/gemini_provider.py).
- **Code Highlights**:
  ```python
  # Cấu hình stop sequences ép mô hình dừng ngay khi hoàn thành Action
  response = self.model.generate_content(
      full_prompt,
      generation_config={"stop_sequences": ["Observation:", "Observation 1:", "Observation 2:", "Observation 3:", "\nObservation"]}
  )
  ```
  ```python
  # Tích lũy số lượng token tiêu thụ từ phản hồi của LLM trong ReAct Loop
  usage = llm_response.get("usage", {})
  if usage:
      total_prompt_tokens += usage.get("prompt_tokens", 0)
      total_completion_tokens += usage.get("completion_tokens", 0)
      total_tokens += usage.get("total_tokens", 0)
  ```
- **Documentation**: 
  Tôi chịu trách nhiệm phát triển vòng lặp ReAct lõi trong lớp `ReActAgent` và đồng bộ với `GeminiProvider`. Tôi đã triển khai cơ chế dừng thế hệ bằng cấu hình `stop_sequences` để ép mô hình dừng sinh văn bản ngay khi viết xong chữ ký gọi tool `Action: tool_name(...)`, ngăn chặn việc tự bịa ra kết quả `Observation`. Đồng thời, tôi thiết lập cơ chế cộng dồn token tiêu thụ (`prompt_tokens`, `completion_tokens`, `total_tokens`) qua mỗi bước suy luận để truyền siêu dữ liệu về cho phía giao diện Web.

---

## II. Debugging Case Study (10 Points)

*Phân tích một sự cố cụ thể mà bạn gặp phải trong quá trình làm lab thông qua hệ thống log.*

- **Problem Description**: Agent rơi vào vòng lặp vô hạn và vượt quá số bước tối đa khi người dùng hỏi các câu hỏi thông tin xung quanh Vinpearl Nha Trang.
- **Log Source**: `logs/2026-06-01.log`
  ```json
  {"timestamp": "2026-06-01T09:45:02.523535", "event": "TOOL_EXECUTION_START", "data": {"tool": "Tôi sẽ sử dụng công cụ search_nearby_attractions...", "args": {}}}
  {"timestamp": "2026-06-01T09:45:02.523920", "event": "TOOL_EXECUTION_END", "data": {"error": "Không tìm thấy công cụ 'Tôi sẽ sử dụng công cụ...'"}}
  ```
- **Diagnosis**: Mô hình Gemini thường viết thêm câu hội thoại dẫn dắt trước dòng gọi tool thực tế (như: *Tôi sẽ dùng công cụ search_nearby_attractions để tìm kiếm... \n Action: search_nearby_attractions(...)*). Bộ phân tích cũ cắt chuỗi theo dấu ngoặc đơn mở đầu tiên, khiến toàn bộ câu dẫn dắt này bị gộp vào làm tên công cụ, dẫn tới lỗi thực thi hệ thống và khiến Agent bị treo.
- **Solution**: Tôi đã tối ưu lại bộ phân tích cú pháp bằng cách duyệt qua danh sách các công cụ đã đăng ký (`self.tools`) và thực hiện đối khớp an toàn dựa trên Regex biểu thức chính quy `rf"\b{t_name}\s*\("`. Điều này giúp loại bỏ 100% các câu dẫn rác và bóc tách chính xác tên công cụ thực tế.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Phản ánh sự khác biệt về năng lực lập luận giữa Chatbot truyền thống và ReAct Agent.*

1. **Reasoning**: Khối `Thought` đóng vai trò là một "bảng nháp tư duy" giúp Agent biết rõ mục tiêu của bước hiện tại, đánh giá thông tin nào còn thiếu và đưa ra lựa chọn công cụ phù hợp. So với Chatbot chỉ trả lời trực tiếp bằng phỏng đoán, cơ chế lập luận giúp Agent hạn chế tối đa ảo giác (hallucination).
2. **Reliability**: Trong trường hợp người dùng đưa ra các câu hỏi quá mơ hồ hoặc sai định dạng ngày tháng mà không có ràng buộc chặt chẽ trong Prompt, ReAct Agent có thể gọi sai tham số của công cụ và đưa ra kết quả không như mong muốn. Lúc này Chatbot truyền thống có thể phản hồi chung chung tốt hơn, trong khi Agent dễ bị kẹt lỗi.
3. **Observation**: Kết quả trả về từ môi trường (`Observation`) đóng vai trò là dữ liệu thực tế kiểm chứng cho suy luận của Agent. Nếu kết quả rỗng, `Thought` tiếp theo sẽ điều chỉnh hướng tìm kiếm (ví dụ đổi từ khóa) hoặc chuyển sang Final Answer mà không bị kẹt.

---

## IV. Future Improvements (5 Points)

*Cách bạn sẽ mở rộng hệ thống này cho một môi trường AI Agent thực tế lớn.*

- **Scalability**: Triển khai hàng đợi bất đồng bộ (như Celery / RabbitMQ) để xử lý các cuộc gọi công cụ tốn nhiều thời gian hoặc tương tác bên ngoài mà không chặn luồng Web Server.
- **Safety**: Xây dựng một mô hình LLM kiểm duyệt độc lập (Supervisor Agent) để giám sát và đánh giá an toàn bảo mật đối với các câu lệnh công cụ sinh ra bởi Agent trước khi thực thi.
- **Performance**: Áp dụng cơ chế Vector DB (như Chroma/Qdrant) để thực hiện Semantic Search trên danh sách các công cụ trong trường hợp số lượng công cụ lên tới hàng trăm, giúp Agent chọn công cụ chính xác hơn.
