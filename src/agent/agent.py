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
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5, max_tool_calls: int = 3):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Trả về system prompt chi tiết hướng dẫn LLM cách suy nghĩ và hành động theo mô hình ReAct.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""Bạn là một Trợ lý Du lịch thông minh, chuyên nghiệp và tận tâm tại hệ thống nghỉ dưỡng Vinpearl Nha Trang.
Bạn có quyền truy cập vào các công cụ (tools) sau để tìm kiếm dữ liệu thực tế và hỗ trợ khách hàng:

{tool_descriptions}

📅 BỐI CẢNH THỜI GIAN THỰC TẾ:
- Hôm nay là thứ Hai, **2026-06-01** (ngày 1 tháng 6 năm 2026).
- Mọi mốc thời gian tương đối do khách hàng đưa ra phải được quy đổi chính xác dựa trên ngày hôm nay. Ví dụ:
  + "Cuối tuần tới": Thứ Sáu 2026-06-05 đến Chủ Nhật 2026-06-07 (vì hôm nay là đầu tuần ngày 01/06/2026).
  + "Cuối tuần này": Thứ Sáu 2026-06-05 đến Chủ Nhật 2026-06-07.
  + "Ngày mai": 2026-06-02.

🛡️ NGUYÊN TẮC GIỚI HẠN PHẠM VI (GUARDRAILS & ON-TOPIC ONLY):
- Bạn CHỈ hỗ trợ và trả lời các chủ đề về dịch vụ nghỉ dưỡng, phòng nghỉ, biệt thự, ăn uống, spa, đi lại, địa điểm giải trí và lịch trình du lịch tại Vinpearl Nha Trang.
- Tuyệt đối KHÔNG hỗ trợ các chủ đề ngoài luồng (như làm toán, viết code, dịch thuật văn bản chung, khoa học công nghệ, chính trị, công thức nấu ăn không liên quan...).
- Đối với bất kỳ câu hỏi ngoài chủ đề, bạn PHẢI từ chối ngay lập tức ở lượt suy nghĩ đầu tiên mà không sử dụng bất kỳ công cụ nào bằng cú pháp Final Answer trực tiếp:
  "Tôi là Trợ lý ảo hỗ trợ đặt phòng và thiết kế lịch trình chuyên nghiệp tại Vinpearl Nha Trang. Tôi chỉ có thể hỗ trợ các thông tin liên quan đến dịch vụ nghỉ dưỡng, ẩm thực, vui chơi và lịch trình du lịch tại Vinpearl Nha Trang. Xin vui lòng đặt các câu hỏi liên quan đến chủ đề này!"

🔄 QUY TRÌNH SUY LUẬN REACT NGHIÊM NGẶT (Thought-Action-Observation):
Nếu câu hỏi ĐÚNG CHỦ ĐỀ, bạn bắt buộc phải suy luận và thu thập dữ liệu qua từng bước. Định dạng mỗi bước phải tuân thủ chính xác 100% cú pháp sau:

Thought: [Dòng suy nghĩ của bạn. Bạn phân tích xem khách hàng cần gì, dữ liệu nào đang thiếu và chọn công cụ nào phù hợp nhất để gọi]
Action: tên_công_cụ(tham_số_1="giá_trị", tham_số_2=giá_trị)
Observation: [Kết quả phản hồi thực tế từ hệ thống. Bạn KHÔNG ĐƯỢC tự viết phần này, hệ thống sẽ tự trả về]

⚠️ LƯU Ý QUAN TRỌNG VỀ ĐỊNH DẠNG PHẢN HỒI:
1. Ở mỗi lượt trả lời, bạn CHỈ ĐƯỢC viết duy nhất 1 cặp Thought và Action. Hãy DỪNG viết ngay sau dấu ngoặc đóng `)` của dòng Action để hệ thống thực thi công cụ và trả về Observation. Tuyệt đối không được viết trước Observation hay viết trước Final Answer nếu chưa chạy công cụ.
2. Tuyệt đối KHÔNG bao bọc cú pháp dòng Action trong bất kỳ ký tự Markdown nào (không dùng ```python hay ```json hay ` xung quanh Action). Ví dụ viết đúng:
   Action: search_rooms(location="Nha Trang", max_price=5000000, adults=2)
3. Bạn CHỈ được đưa ra câu trả lời cuối cùng khi đã hoàn thành việc gọi công cụ và có đầy đủ dữ liệu thực tế:
   Final Answer: [Câu trả lời hoàn chỉnh, trình bày đẹp mắt bằng Markdown, thân thiện, trung thực dựa trên kết quả thật của Observation. Hãy so sánh giá các phòng, làm nổi bật inclusions và chèn bảng lịch trình du lịch cụ thể]
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
        tool_calls_count = 0
        final_answer = ""
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        
        while steps < self.max_steps:
            steps += 1
            step_info = {"step": steps, "thought": "", "action": "", "observation": ""}
            
            # Gọi LLM để sinh bước suy nghĩ và hành động tiếp theo
            logger.log_event("LLM_CALL_START", {"step": steps})
            
            # Cấu hình stop sequences để ép mô hình dừng ngay khi viết xong Action hoặc chuẩn bị viết Observation
            llm_response = self.llm.generate(current_context, system_prompt=self.get_system_prompt())
            content = llm_response.get("content", "").strip()
            logger.log_event("LLM_CALL_END", {"step": steps, "latency_ms": llm_response.get("latency_ms")})
            
            # Tích lũy số lượng token tiêu thụ từ phản hồi của LLM
            usage = llm_response.get("usage", {})
            if usage:
                total_prompt_tokens += usage.get("prompt_tokens", 0)
                total_completion_tokens += usage.get("completion_tokens", 0)
                total_tokens += usage.get("total_tokens", 0)
            
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
                    # Kiểm tra và ngăn chặn nếu vượt quá giới hạn gọi Tool trong phiên chạy
                    if tool_calls_count >= self.max_tool_calls:
                        logger.log_event("TOOL_CALL_LIMIT_REACHED", {"limit": self.max_tool_calls})
                        observation = f"Hệ thống cảnh báo: Bạn đã đạt giới hạn gọi công cụ tối đa ({self.max_tool_calls} lần). Bạn không được gọi thêm bất kỳ công cụ nào khác lúc này. Hãy đưa ra câu trả lời Final Answer tốt nhất ngay lập tức cho khách hàng dựa trên những thông tin bạn đã tìm thấy ở các bước trước."
                    else:
                        tool_calls_count += 1
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
            "total_steps": steps,
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens
            }
        }

    def _parse_action(self, action_str: str) -> tuple:
        """
        Bóc tách tên tool và các đối số từ chuỗi gọi tool dạng: tool_name(key1="val1", key2=val2)
        Sử dụng AST (Abstract Syntax Tree) để phân tích cú pháp an toàn và chính xác, 
        kết hợp tìm kiếm tên tool hợp lệ để bỏ qua các đoạn text rác xung quanh.
        """
        import ast

        # Làm sạch các ký tự lạ, khoảng trắng hoặc code block dư thừa xung quanh chuỗi gọi hàm
        action_str = action_str.strip().replace("`", "")

        # 1. Tìm xem có tên tool hợp lệ nào được gọi không
        tool_name = None
        args_str = ""
        first_paren = -1
        
        for t in self.tools:
            t_name = t['name']
            # Tìm pattern: tên tool theo sau bởi khoảng trắng tùy ý và dấu (
            pattern = rf"\b{t_name}\s*\("
            match = re.search(pattern, action_str)
            if match:
                tool_name = t_name
                first_paren = match.end() - 1
                break
                
        if not tool_name:
            # Fallback: nếu không tìm thấy tool trong danh sách, thử tìm chữ đầu tiên trước dấu (
            first_paren = action_str.find("(")
            if first_paren != -1:
                potential_name = action_str[:first_paren].strip()
                # Lấy từ cuối cùng trong potential_name làm tên tool
                words = re.findall(r"\b\w+\b", potential_name)
                if words:
                    tool_name = words[-1]
            
        if not tool_name or first_paren == -1:
            return None, {}

        # 2. Tìm ngoặc đơn đóng tương ứng (Paren-Depth Tracking) để lấy chuỗi đối số chính xác
        paren_depth = 1
        last_paren = -1
        for idx in range(first_paren + 1, len(action_str)):
            if action_str[idx] == "(":
                paren_depth += 1
            elif action_str[idx] == ")":
                paren_depth -= 1
                if paren_depth == 0:
                    last_paren = idx
                    break
                    
        if last_paren == -1:
            # Fallback nếu thiếu ngoặc đóng
            args_str = action_str[first_paren + 1:].strip()
        else:
            args_str = action_str[first_paren + 1 : last_paren].strip()
            
        if not args_str:
            return tool_name, {}

        # 3. Phân tích cú pháp đối số sử dụng AST (Abstract Syntax Tree) để hỗ trợ hoàn hảo cấu trúc phức tạp
        try:
            # Wrap trong một hàm dummy để tạo biểu thức Python hợp lệ
            tree = ast.parse(f"dummy({args_str})")
            call_node = tree.body[0].value
            args = {}
            for kw in call_node.keywords:
                args[kw.arg] = ast.literal_eval(kw.value)
            return tool_name, args
        except Exception as e:
            # Fallback regex nếu AST parse thất bại (ví dụ: chuỗi bị cắt hoặc lỗi cú pháp nhẹ)
            logger.log_event("AST_PARSING_FAILED", {"error": str(e), "args_str": args_str})
            args = {}
            pattern = r"(\w+)\s*=\s*('[^']*'|\"[^\"]*\"|\[[^\]]*\]|[^,]+)"
            for k, v in re.findall(pattern, args_str):
                k = k.strip()
                v = v.strip()
                if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                    args[k] = v[1:-1]
                elif v.startswith("[") and v.endswith("]"):
                    try:
                        list_items = []
                        item_pattern = r"'([^']*)'|\"([^\"]*)\""
                        for item_match in re.findall(item_pattern, v):
                            item = item_match[0] or item_match[1]
                            list_items.append(item)
                        args[k] = list_items
                    except Exception:
                        args[k] = []
                else:
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

