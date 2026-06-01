# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Đức Mạnh
- **Student ID**: 2A202600724
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Mô tả đóng góp cụ thể của bạn đối với codebase (ví dụ: phát triển bộ dữ liệu kiểm thử, viết tích hợp kiểm thử tự động, cấu hình Guardrails hệ thống).*

- **Modules Implemented**: [packages.json](file:///c:/code/VinUni/Day-3-Lab-Chatbot-vs-react-agent/data/packages.json) (Mock Database), [attractions.json](file:///c:/code/VinUni/Day-3-Lab-Chatbot-vs-react-agent/data/attractions.json), [test_agent_vinpearl.py](file:///c:/code/VinUni/Day-3-Lab-Chatbot-vs-react-agent/tests/test_agent_vinpearl.py) (Kiểm thử luồng ReAct trên terminal), và hoàn thiện Báo cáo Nhóm.
- **Code Highlights**:
  ```python
  # Thiếp lập chốt chặn từ chối trực tiếp đối với câu hỏi ngoài chủ đề du lịch Vinpearl
  if not is_on_topic(user_input):
      return {
          "answer": "Tôi là Trợ lý ảo hỗ trợ đặt phòng và thiết kế lịch trình chuyên nghiệp tại Vinpearl Nha Trang. Tôi chỉ có thể hỗ trợ các thông tin liên quan đến dịch vụ nghỉ dưỡng, ẩm thực, vui chơi và lịch trình du lịch tại Vinpearl Nha Trang. Xin vui lòng đặt các câu hỏi liên quan đến chủ đề này!",
          "steps": [],
          "total_steps": 0
      }
  ```
- **Documentation**: 
  Tôi chịu trách nhiệm xây dựng bộ dữ liệu mock phong phú gồm 9 gói phòng nghỉ dưỡng cao cấp với lịch bận chi tiết (`blocked_dates`) và 13 điểm giải trí/spa phân loại rõ ràng đối tượng khách hàng (Người lớn/Trẻ nhỏ). Tôi thiết lập chốt chặn chủ đề (Vietnamese Semantic Guardrails) để ngăn ngừa các câu hỏi ngoài lề gây lãng phí tài nguyên LLM. Ngoài ra, tôi phát triển script kiểm thử tự động `test_agent_vinpearl.py` để mô phỏng hoàn chỉnh cuộc hội thoại ReAct và đánh giá hiệu quả lập luận của hệ thống.

---

## II. Debugging Case Study (10 Points)

*Phân tích một sự cố cụ thể mà bạn gặp phải trong quá trình làm lab thông qua hệ thống log hoặc kiểm thử.*

- **Problem Description**: Khi người dùng hỏi các câu hỏi không liên quan (ví dụ: viết code Python, giải toán hoặc hỏi công thức nấu ăn), Agent vẫn cố gắng suy luận Thought và gọi bừa bãi các công cụ như `search_nearby_attractions` để tìm kiếm thông tin, dẫn tới lãng phí tài nguyên và chi phí API đáng kể.
- **Log Source**: `logs/2026-06-01.log`
  ```json
  {"timestamp": "2026-06-01T07:53:25.244316", "event": "AGENT_START", "data": {"input": "hãy viết cho tôi một đoạn mã python sắp xếp mảng"}}
  {"timestamp": "2026-06-01T07:53:43.662142", "event": "TOOL_EXECUTION_START", "data": {"tool": "search_nearby_attractions", "args": {"location": "python"}}}
  ```
- **Diagnosis**: Hệ thống Prompt chưa được tối ưu hóa đầy đủ để chặn các câu hỏi ngoài lề. LLM luôn cố gắng thỏa mãn người dùng bằng cách áp đặt câu hỏi vào một trong những công cụ có sẵn, dẫn tới hành vi gọi công cụ sai mục đích một cách mù quáng.
- **Solution**: Tôi đã tối ưu hóa lại System Prompt trong `agent.py`, bổ sung phần nguyên tắc giới hạn phạm vi nghiêm ngặt (Guardrails & On-Topic Only). Tôi yêu cầu mô hình phải từ chối thẳng thắn ngay từ suy nghĩ đầu tiên (`Thought 1`) bằng cú pháp `Final Answer` trực tiếp mà tuyệt đối không gọi bất kỳ công cụ nào khi phát hiện câu hỏi ngoài lề. Điều này giúp ngăn chặn 100% việc rò rỉ token và chi phí ngoài ý muốn.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Phản ánh sự khác biệt về năng lực lập luận giữa Chatbot truyền thống và ReAct Agent.*

1. **Reasoning**: Thought trong ReAct giúp mô hình suy nghĩ trước khi hành động, tương tự như bộ não con người. Nó phân tích ngữ cảnh thời gian (như quy đổi "ngày mai" hoặc "cuối tuần sau" thành ngày cụ thể dựa trên mốc 2026-06-01) để gọi công cụ với tham số ngày chính xác nhất. Chatbot truyền thống hoàn toàn bỏ qua bước quy đổi thời gian thực tế này.
2. **Reliability**: ReAct Agent có độ ổn định nghiệp vụ cao vì kết quả được xác thực bởi dữ liệu thật (Observation). Chatbot baseline thường đưa ra những câu trả lời "có vẻ đúng" nhưng thực tế lại hoàn toàn giả mạo, làm giảm độ tin cậy của doanh nghiệp.
3. **Observation**: Môi trường phản hồi qua các quan sát (Observations) giúp mô hình kiểm chứng lý thuyết. Nếu phòng đã bị bận vào ngày khách yêu cầu, Agent sẽ lập tức tìm phòng trống khác dựa trên phản hồi đó.

---

## IV. Future Improvements (5 Points)

*Cách bạn sẽ mở rộng hệ thống này cho một môi trường AI Agent thực tế lớn.*

- **Scalability**: Triển khai cơ chế phân phối tải (Load Balancing) cho Web Server và chạy các bài kiểm thử chịu tải nâng cao để đảm bảo hệ thống phục vụ tốt hàng ngàn yêu cầu chat đồng thời vào mùa cao điểm du lịch.
- **Safety**: Xây dựng giải pháp giám sát chi phí thời gian thực (Billing Alert & Rate Limiting) cho từng Session ID của khách hàng nhằm tránh tình trạng lạm dụng API hoặc tấn công spam gây quá tải hệ thống.
- **Performance**: Chuyển đổi kịch bản kiểm thử tự động thành các luồng CI/CD (Continuous Integration), giúp hệ thống tự động kiểm duyệt độ chính xác của câu trả lời mỗi khi cập nhật cơ sở dữ liệu phòng nghỉ hoặc mã nguồn lõi.
