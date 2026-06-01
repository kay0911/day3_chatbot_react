import os
import re
import ast
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.tools.vinpearl_tools import search_rooms, search_nearby_attractions, filter_packages

class ReActAgent:
    """
    A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Implements AST-based parameter parsing to avoid regex errors on complex types.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Implement the system prompt that instructs the agent to follow ReAct.
        Should include:
        1.  Available tools and their descriptions.
        2.  Format instructions: Thought, Action, Observation.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""You are an intelligent assistant for Vinpearl resort bookings and local attractions.
You have access to the following tools:
{tool_descriptions}

You MUST follow the ReAct (Reasoning and Acting) framework. For each step of your reasoning, follow this exact format:

Thought: Your line of reasoning about what to do next.
Action: tool_name(arg1=val1, arg2=val2, ...)
Observation: The result of executing the tool (do not write this yourself, the system will provide it).

Repeat the Thought/Action/Observation steps as needed to solve the user request.
Once you have enough information, output your final response in this format:

Final Answer: [Your complete response to the user in Vietnamese, summarizing the results, package prices, and attractions logically]

Example:
Thought: Tôi cần tìm phòng ở Nha Trang trước.
Action: search_rooms(location="Nha Trang", checkin="2026-06-05", checkout="2026-06-07", guests=2)
Observation: [{{"id": "PKG-A", "name": "Deluxe Room", "price_per_night": 1500000, "includes": ["Room Only"]}}]
Thought: Tôi sẽ lọc gói phòng có bữa ăn sáng.
Action: filter_packages(packages=[{{"id": "PKG-A", "name": "Deluxe Room", "price_per_night": 1500000, "includes": ["Room Only"]}}], includes=["Breakfast"])
Observation: []
Thought: Không có phòng nào có ăn sáng. Tôi sẽ trả lời khách hàng.
Final Answer: Rất tiếc, hiện tại không có phòng nào bao gồm bữa sáng tại Nha Trang cho ngày bạn yêu cầu. Chỉ có phòng Deluxe Room (không bao gồm ăn sáng) với giá 1.500.000 VNĐ/đêm.

Note: When calling filter_packages, pass the exact list of packages returned by the previous search_rooms call. Do not modify the package structure.
"""

    def run(self, user_input: str) -> str:
        """
        Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        self.history = []
        steps = 0
        final_response = "Xin lỗi, tôi chưa thể hoàn thành yêu cầu của bạn."

        while steps < self.max_steps:
            # Build current prompt from history
            prompt = f"User Query: {user_input}\n"
            if self.history:
                prompt += "\n".join(self.history) + "\n"
            prompt += "Thought:"
            
            # Generate LLM response
            response = self.llm.generate(prompt, system_prompt=self.get_system_prompt())
            
            # Track LLM request metrics
            tracker.track_request(
                provider=response.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=response.get("usage", {}),
                latency_ms=response.get("latency_ms", 0)
            )
            
            content = response["content"].strip()
            
            # Format text properly with Thought prefix
            text = content
            if not text.startswith("Thought:"):
                text = "Thought: " + text
                
            self.history.append(text)
            
            # Check for Final Answer
            if "Final Answer:" in text:
                final_response = text.split("Final Answer:")[-1].strip()
                break
                
            # Parse Action
            # Use re.DOTALL to support multiline argument blocks (e.g. nested lists/dicts)
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", text, re.DOTALL)
            if action_match:
                tool_name = action_match.group(1)
                args_str = action_match.group(2).strip()
                
                # Parse arguments using AST as described in the report
                try:
                    tree = ast.parse(f"dummy({args_str})")
                    call_node = tree.body[0].value
                    args = {}
                    for kw in call_node.keywords:
                        args[kw.arg] = ast.literal_eval(kw.value)
                except Exception as e:
                    # Parse error logging and recovery
                    error_msg = f"Parser Error - Could not parse arguments for tool '{tool_name}' using AST. Details: {e}. Output args string was: {args_str}"
                    logger.log_event("TOOL_EXECUTION_END", {"error": error_msg})
                    self.history.append(f"Observation: Lỗi khi thực thi công cụ {tool_name}: {error_msg}")
                    steps += 1
                    continue
                
                # Execute tool
                observation = self._execute_tool(tool_name, args)
                self.history.append(f"Observation: {observation}")
            else:
                # If the agent didn't output an Action or Final Answer, prompt it to give Final Answer or Action
                self.history.append("Observation: Hệ thống yêu cầu bạn tiếp tục suy luận và đưa ra Action: tool_name(...) hoặc Final Answer: [kết quả].")

            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps})
        return final_response

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Helper method to execute tools by name.
        """
        logger.log_event("TOOL_EXECUTION_START", {"tool": tool_name, "args": args})
        
        try:
            if tool_name == "search_rooms":
                result = search_rooms(**args)
            elif tool_name == "search_nearby_attractions":
                result = search_nearby_attractions(**args)
            elif tool_name == "filter_packages":
                result = filter_packages(**args)
            else:
                raise ValueError(f"Tool {tool_name} not found.")
                
            logger.log_event("TOOL_EXECUTION_END", {"result": result})
            return str(result)
        except Exception as e:
            logger.log_event("TOOL_EXECUTION_END", {"error": str(e)})
            return f"Lỗi khi thực thi công cụ {tool_name}: {e}"
