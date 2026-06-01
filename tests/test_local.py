import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.local_provider import LocalProvider

def test_local_phi3():
    load_dotenv()
    model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
    
    print(f"--- Testing Local Provider with Phi-3 ---")
    print(f"Model Path: {model_path}")
    
    if not os.path.exists(model_path):
        print(f"❌ Error: Model file not found at {model_path}")
        print("Please download it from Hugging Face and place it in the models/ folder.")
        return

    try:
        provider = LocalProvider(model_path=model_path)
        
        print("\n" + "="*50)
        print("🤖 CHAT TRỰC TIẾP VỚI LOCAL MODEL PHI-3 (OFFLINE)")
        print("Nhập câu hỏi của bạn dưới đây. Gõ 'exit' hoặc 'quit' để thoát.")
        print("="*50 + "\n")
        
        while True:
            try:
                prompt = input("\nUser: ").strip()
                if not prompt:
                    continue
                if prompt.lower() in ["exit", "quit"]:
                    print("Tạm biệt!")
                    break
                    
                print("Assistant: ", end="", flush=True)
                for chunk in provider.stream(prompt):
                    print(chunk, end="", flush=True)
                print()
                
            except KeyboardInterrupt:
                print("\nTạm biệt!")
                break
        
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")

if __name__ == "__main__":
    test_local_phi3()
