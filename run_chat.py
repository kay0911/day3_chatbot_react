import os
from llama_cpp import Llama

class LocalChatAgent:
    """Class quản lý giao tiếp với mô hình ngôn ngữ local."""
    
    def __init__(self, model_path: str):
        print("⏳ Đang tải model vào bộ nhớ...")
        # Khởi tạo mô hình
        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,       # Giới hạn bối cảnh (context window) của Phi-3
            n_threads=4,      # Số luồng CPU sử dụng (có thể tăng lên nếu CPU mạnh)
            verbose=False     # Tắt các log kỹ thuật của C++ để terminal sạch sẽ
        )
        print("✅ Tải model thành công! Gõ 'quit' hoặc 'q' để thoát.\n")
        print("-" * 50)

    def chat_loop(self):
        """Vòng lặp nhận input từ người dùng và in kết quả trả về."""
        while True:
            try:
                user_input = input("\n🧑 Bạn: ")
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Tạm biệt!")
                    break

                if not user_input.strip():
                    continue

                # Cấu trúc prompt chuẩn dành riêng cho mô hình Phi-3
                prompt = f"<|user|>\n{user_input}<|end|>\n<|assistant|>"

                print("🤖 Agent: ", end="", flush=True)

                # Sử dụng generator để stream text ra terminal theo thời gian thực
                stream = self.llm(
                    prompt,
                    max_tokens=512,
                    stop=["<|user|>", "<|end|>"],
                    stream=True
                )

                for output in stream:
                    text = output["choices"][0]["text"]
                    print(text, end="", flush=True)
                print() # Xuống dòng khi agent hoàn thành câu trả lời

            except KeyboardInterrupt:
                # Xử lý khi người dùng bấm Ctrl+C
                print("\n\n🔌 Đã ngắt kết nối. Tạm biệt!")
                break

if __name__ == "__main__":
    # Đường dẫn trỏ trực tiếp đến file ở thư mục gốc
    MODEL_PATH = "Phi-3-mini-4k-instruct-q4.gguf"

    if not os.path.exists(MODEL_PATH):
        print(f"❌ Không tìm thấy file '{MODEL_PATH}'. Vui lòng kiểm tra lại!")
    else:
        agent = LocalChatAgent(MODEL_PATH)
        agent.chat_loop()