import os
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Trả về system prompt chi tiết hướng dẫn LLM cách suy nghĩ và hành động theo mô hình ReAct.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""Bạn là một Trợ lý Du lịch thông minh, chuyên nghiệp chuyên hỗ trợ đặt phòng và thiết kế lịch trình tại hệ thống nghỉ dưỡng Vinpearl Nha Trang.
Bạn có quyền truy cập vào các công cụ (tools) sau để trả lời câu hỏi của khách hàng một cách chính xác nhất:

{tool_descriptions}

NGUYÊN TẮC GIỚI HẠN PHẠM VI (GUARDRAILS & ON-TOPIC ONLY):
- Bạn CHỈ ĐƯỢC PHÉP hỗ trợ và trả lời các câu hỏi liên quan trực tiếp đến dịch vụ nghỉ dưỡng, phòng ở, biệt thự, ăn uống, spa, đi lại, địa điểm giải trí và lịch trình du lịch tại Vinpearl Nha Trang.
- Tuyệt đối KHÔNG trả lời bất kỳ câu hỏi nào ngoài phạm vi trên (ví dụ: làm toán, viết code, dịch thuật văn bản chung, hỏi đáp kiến thức khoa học chung, chính trị, tư vấn công nghệ, công thức nấu ăn không liên quan...).
- Nếu khách hàng đặt câu hỏi ngoài phạm vi, bạn PHẢI từ chối ngay lập tức ở lượt trả lời đầu tiên mà không sử dụng bất kỳ công cụ nào, bằng cách đưa ra Final Answer trực tiếp với nội dung:
  "Tôi là Trợ lý ảo hỗ trợ đặt phòng và thiết kế lịch trình chuyên nghiệp tại Vinpearl Nha Trang. Tôi chỉ có thể hỗ trợ các thông tin liên quan đến dịch vụ nghỉ dưỡng, ẩm thực, vui chơi và lịch trình du lịch tại Vinpearl Nha Trang. Xin vui lòng đặt các câu hỏi liên quan đến chủ đề này!"

QUY TRÌNH SUY NGHĨ VÀ SUY LUẬN (ReAct Loop):
Khi nhận được câu hỏi từ khách hàng và câu hỏi đó ĐÚNG CHỦ ĐỀ, bạn PHẢI thực hiện suy luận từng bước theo định dạng nghiêm ngặt sau. Tuyệt đối không được gộp nhiều bước hoặc tự tạo kết quả Observation:

Thought: [Dòng suy nghĩ của bạn để giải quyết câu hỏi ở bước này. Bạn cần phân tích xem cần thông tin gì và chọn công cụ nào phù hợp]
Action: tên_công_cụ(tham_số_1="giá_trị", tham_số_2=giá_trị)
Observation: [Hệ thống sẽ tự động chạy công cụ và trả về kết quả ở đây. Bạn tuyệt đối KHÔNG ĐƯỢC tự viết phần này]

Bạn sẽ lặp lại chu kỳ trên từng bước một. CHỈ khi nào bạn đã nhận được đầy đủ kết quả thực tế từ phần Observation và có câu trả lời chính xác, bạn mới được đưa ra câu trả lời cuối cùng bằng định dạng:

Final Answer: [Nội dung câu trả lời hoàn chỉnh, chi tiết, chính xác dựa trên dữ liệu thật và thân thiện dành cho khách hàng]

LƯU Ý CỰC KỲ QUAN TRỌNG:
- Ở mỗi lượt trả lời, bạn chỉ được viết duy nhất 1 cặp Thought và Action. Hãy dừng lại ngay sau khi viết xong dòng Action để hệ thống thực thi công cụ và trả về Observation. Tuyệt đối KHÔNG viết sẵn Observation hay Final Answer nếu chưa có kết quả thật từ công cụ.
- Trả lời trung thực dựa trên kết quả trả về của công cụ. Không được tự bịa ra thông tin phòng hay mức giá không có trong dữ liệu thật.
- Trong phần Action, bạn phải ghi đúng cú pháp gọi hàm Python. Ví dụ: `search_rooms(location="Nha Trang", max_price=5000000, adults=2)`
"""

    def run(self, user_input: str) -> Dict[str, Any]:
        """
        Thực hiện vòng lặp ReAct:
        1. Gửi prompt hiện tại tới LLM để nhận Thought + Action (hoặc Final Answer).
        2. Tách Action và thực thi Tool tương ứng.
        3. Nhận kết quả Observation, bổ sung vào lịch sử cuộc trò chuyện và tiếp tục bước tiếp theo.
        4. Trả về câu trả lời cuối cùng kèm danh sách chi tiết các bước để hiển thị trực quan lên UI.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        self.history = []
        current_context = f"Yêu cầu của khách hàng: {user_input}\n\nBắt đầu chu trình suy luận ReAct:\n"
        steps_taken = []
        
        steps = 0
        final_answer = ""
        
        while steps < self.max_steps:
            steps += 1
            step_info = {"step": steps, "thought": "", "action": "", "observation": ""}
            
            # Gọi LLM để sinh bước suy nghĩ và hành động tiếp theo
            logger.log_event("LLM_CALL_START", {"step": steps})
            
            # Cấu hình stop sequences để ép mô hình dừng ngay khi viết xong Action hoặc chuẩn bị viết Observation
            llm_response = self.llm.generate(current_context, system_prompt=self.get_system_prompt())
            content = llm_response.get("content", "").strip()
            logger.log_event("LLM_CALL_END", {"step": steps, "latency_ms": llm_response.get("latency_ms")})
            
            # Tách Thought (chấp nhận cả định dạng "1. Thought:" hoặc "Thought:")
            thought_match = re.search(r"(?:\d+\.)?\s*Thought(?:\s*\d+)?:?\s*(.*?)(?=(?:\d+\.)?\s*Action|Final Answer|$)", content, re.DOTALL | re.IGNORECASE)
            
            # Tách Action (chấp nhận cả định dạng "2. Action:" hoặc "Action:")
            action_match = re.search(r"(?:\d+\.)?\s*Action(?:\s*\d+)?:?\s*(.*?)(?=(?:\d+\.)?\s*Observation|Final Answer|$)", content, re.DOTALL | re.IGNORECASE)
            
            thought = thought_match.group(1).strip() if thought_match else "Đang suy nghĩ..."
            # Dọn dẹp ký tự thừa ở cuối Thought nếu có
            thought = re.sub(r"\s*\d+\.\s*$", "", thought).strip()
            step_info["thought"] = thought
            current_context += f"\nThought {steps}: {thought}\n"
            
            # PHÂN TÍCH HÀNH ĐỘNG (ACTION) TRƯỚC:
            # Nếu LLM đề xuất Action -> Luôn ưu tiên gọi Tool kể cả khi LLM có tự viết Final Answer đi kèm (để chống hallucination)
            if action_match and action_match.group(1).strip():
                action_str = action_match.group(1).strip()
                # Dọn dẹp ký tự thừa ở cuối Action nếu có
                action_str = re.sub(r"\s*\d+\.\s*$", "", action_str).strip()
                step_info["action"] = action_str
                current_context += f"Action {steps}: {action_str}\n"
                
                # Phân tích tên công cụ và tham số
                tool_name, tool_args = self._parse_action(action_str)
                
                if tool_name:
                    logger.log_event("TOOL_EXECUTION_START", {"tool": tool_name, "args": tool_args})
                    observation = self._execute_tool(tool_name, tool_args)
                    logger.log_event("TOOL_EXECUTION_END", {"tool": tool_name, "observation_summary": str(observation)[:120]})
                else:
                    observation = f"Lỗi cú pháp gọi công cụ: '{action_str}'. Vui lòng gọi lại theo định dạng chính xác: tool_name(key1=value1, key2=value2)."
                    
                step_info["observation"] = observation
                current_context += f"Observation {steps}: {observation}\n"
                steps_taken.append(step_info)
                
            else:
                # Nếu KHÔNG có Action nào được đề xuất -> Tìm kiếm câu trả lời cuối cùng
                final_match = re.search(r"Final Answer:\s*(.*)", content, re.DOTALL | re.IGNORECASE)
                if final_match:
                    final_answer = final_match.group(1).strip()
                    step_info["final_answer"] = final_answer
                    steps_taken.append(step_info)
                    current_context += f"Final Answer: {final_answer}\n"
                    break
                else:
                    # Nếu không có định dạng mong muốn, coi như phản hồi trực tiếp
                    final_answer = content.replace("Final Answer:", "").strip()
                    step_info["final_answer"] = final_answer
                    steps_taken.append(step_info)
                    break
                    
        # Nếu chạy hết số bước mà chưa có Final Answer, tự động tạo câu trả lời tổng hợp từ các thông tin đã có
        if not final_answer:
            logger.log_event("AGENT_MAX_STEPS_REACHED", {"steps": steps})
            final_answer = "Rất tiếc, tôi chưa thể hoàn thành toàn bộ yêu cầu của bạn do vượt quá số bước suy luận cho phép. Tuy nhiên, dựa trên các thông tin đã tìm kiếm được, tôi xin tóm tắt các gói phòng phù hợp nhất cho bạn tại Vinpearl Nha Trang..."
            
        logger.log_event("AGENT_END", {"steps": steps, "final_answer_length": len(final_answer)})
        
        return {
            "answer": final_answer,
            "steps": steps_taken,
            "total_steps": steps
        }

    def _parse_action(self, action_str: str) -> tuple:
        """
        Bóc tách tên tool và các đối số từ chuỗi gọi tool dạng: tool_name(key1="val1", key2=val2)
        """
        # Trích xuất tên tool và chuỗi chứa đối số
        match = re.match(r"(\w+)\s*\((.*)\)", action_str, re.DOTALL)
        if not match:
            return None, {}
            
        tool_name = match.group(1)
        args_str = match.group(2).strip()
        
        if not args_str:
            return tool_name, {}
            
        # Phân tích cú pháp các đối số sử dụng regex
        # Hỗ trợ dạng key="value", key='value', key=value (số hoặc danh sách)
        args = {}
        # Regex tìm kiếm key = value
        pattern = r"(\w+)\s*=\s*('[^']*'|\"[^\"]*\"|\[[^\]]*\]|[^,]+)"
        for k, v in re.findall(pattern, args_str):
            k = k.strip()
            v = v.strip()
            
            # Giải mã chuỗi chuỗi trích xuất được
            if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                args[k] = v[1:-1]
            elif v.startswith("[") and v.endswith("]"):
                # Danh sách: ví dụ ['VinWonders', 'Spa']
                try:
                    # Clean và parse list đơn giản
                    list_items = []
                    item_pattern = r"'([^']*)'|\"([^\"]*)\""
                    for item_match in re.findall(item_pattern, v):
                        item = item_match[0] or item_match[1]
                        list_items.append(item)
                    args[k] = list_items
                except Exception:
                    args[k] = []
            else:
                # Số hoặc Boolean
                if v.lower() == "true":
                    args[k] = True
                elif v.lower() == "false":
                    args[k] = False
                else:
                    try:
                        if "." in v:
                            args[k] = float(v)
                        else:
                            args[k] = int(v)
                    except ValueError:
                        args[k] = v
                        
        return tool_name, args

    def _execute_tool(self, tool_name: str, args: dict) -> str:
        """
        Thực thi tool động thông qua tên tool và từ điển tham số truyền vào.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                try:
                    func = tool['func']
                    result = func(**args)
                    
                    # Trả về kết quả dạng chuỗi đẹp mắt hoặc JSON để LLM đọc
                    if isinstance(result, (dict, list)):
                        return json.dumps(result, ensure_ascii=False, indent=2)
                    return str(result)
                except Exception as e:
                    return f"Lỗi khi thực thi công cụ {tool_name}: {str(e)}"
                    
        return f"Không tìm thấy công cụ '{tool_name}'."

