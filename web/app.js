document.addEventListener("DOMContentLoaded", () => {
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const chatMessages = document.getElementById("chat-messages");
    const stepsContainer = document.getElementById("steps-container");
    const emptyTelemetry = document.getElementById("empty-telemetry");

    const SESSION_KEY = "vinpearl_chat_session";

    // Load chat history from sessionStorage
    let chatHistory = JSON.parse(sessionStorage.getItem(SESSION_KEY) || "[]");

    // Restore previous messages on page load
    chatHistory.forEach(msg => {
        appendMessage(msg.content, msg.role === "user" ? "user" : "assistant");
    });

    // Send Message
    async function sendMessage(text) {
        if (!text.trim()) return;

        // Add user message to chat
        appendMessage(text, "user");
        chatInput.value = "";

        // Show typing indicator
        const typingIndicator = showTypingIndicator();

        // Clear previous telemetry visualizer
        stepsContainer.innerHTML = "";
        stepsContainer.appendChild(emptyTelemetry);
        emptyTelemetry.style.display = "none";

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000);

            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: text,
                    history: chatHistory
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error("Không thể kết nối đến Web Server.");
            }

            const data = await response.json();
            
            // Remove typing indicator
            typingIndicator.remove();

            // Render Final Answer
            if (data.answer) {
                appendMessage(data.answer, "assistant", data.usage);
                
                // Lưu vào lịch sử hội thoại trong phiên (Session Memory)
                chatHistory.push({ role: "user", content: text });
                chatHistory.push({ role: "assistant", content: data.answer });
                
                // Giới hạn bộ nhớ chỉ lưu 10 tin nhắn gần nhất để tránh phồng token
                if (chatHistory.length > 10) {
                    chatHistory.splice(0, 2);
                }
                sessionStorage.setItem(SESSION_KEY, JSON.stringify(chatHistory));
            } else {
                appendMessage("Xin lỗi, tôi gặp sự cố khi suy luận câu trả lời.", "assistant");
            }

            // Render ReAct Steps in visualizer
            if (data.steps && data.steps.length > 0) {
                renderSteps(data.steps);
            } else {
                emptyTelemetry.style.display = "flex";
                emptyTelemetry.querySelector("p").innerText = "Agent trả lời trực tiếp mà không cần dùng đến công cụ.";
            }

        } catch (error) {
            console.error(error);
            typingIndicator.remove();
            if (error.name === "AbortError") {
                appendMessage("⏳ Hệ thống đang gặp sự cố, phản hồi quá lâu (hơn 60 giây). Bạn thông cảm và thử lại sau nhé!", "assistant");
            } else {
                appendMessage(`❌ Lỗi: ${error.message}. Hãy chắc chắn rằng Web Server đang chạy tại cổng 5000.`, "assistant");
            }
            emptyTelemetry.style.display = "flex";
        }
    }

    // Append standard message in chat bubbles
    function appendMessage(text, sender, usage = null) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", sender);

        if (sender === "assistant") {
            const heading = document.createElement("h3");
            heading.innerText = "🏖️ Vinpearl Travel Agent";
            messageDiv.appendChild(heading);

            // Simple Markdown formatter for bold and lists
            const formattedBody = document.createElement("div");
            formattedBody.innerHTML = formatMarkdown(text);
            messageDiv.appendChild(formattedBody);

            // Render token usage if available
            if (usage && (usage.total_tokens || usage.prompt_tokens || usage.completion_tokens)) {
                const usageDiv = document.createElement("div");
                usageDiv.classList.add("message-usage");
                usageDiv.innerHTML = `
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 5px; display: inline-block; vertical-align: middle;"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>
                    Tiêu thụ: <strong>${usage.total_tokens || 0}</strong> tokens (Prompt: ${usage.prompt_tokens || 0} | Completion: ${usage.completion_tokens || 0})
                `;
                messageDiv.appendChild(usageDiv);
            }
        } else {
            messageDiv.innerText = text;
        }

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Premium markdown compiler with marked.js & custom fallbacks
    function formatMarkdown(text) {
        if (typeof marked !== 'undefined') {
            try {
                return marked.parse(text);
            } catch (e) {
                console.error("Marked parsing error:", e);
            }
        }
        
        // Beautiful fallback regex compiler
        let html = text;
        
        // Escape HTML tags to prevent XSS except the ones we generate
        html = html
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Headers: ###, ##, #
        html = html.replace(/^###\s+(.*)$/gm, "<h3>$1</h3>");
        html = html.replace(/^##\s+(.*)$/gm, "<h2>$1</h2>");
        html = html.replace(/^#\s+(.*)$/gm, "<h1>$1</h1>");

        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

        // Horizontal Rule
        html = html.replace(/^---\s*$/gm, "<hr>");

        // Unordered lists (- or *)
        html = html.replace(/^\s*[-*]\s+(.*)$/gm, "<li>$1</li>");
        html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");

        // Newlines to br
        html = html.replace(/\n/g, "<br>");

        return html;
    }

    // Show Typing Indicator bubble
    function showTypingIndicator() {
        const indicator = document.createElement("div");
        indicator.classList.add("typing-indicator");
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement("div");
            dot.classList.add("typing-dot");
            indicator.appendChild(dot);
        }

        chatMessages.appendChild(indicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return indicator;
    }

    // Render Steps in the Telemetry Panel
    function renderSteps(steps) {
        // Clear panel
        stepsContainer.innerHTML = "";
        
        steps.forEach((step) => {
            const groupDiv = document.createElement("div");
            groupDiv.classList.add("step-card-group");

            const groupTitle = document.createElement("div");
            groupTitle.classList.add("step-group-title");
            groupTitle.innerText = `Bước ${step.step}: Phân tích yêu cầu`;
            groupDiv.appendChild(groupTitle);

            // 1. Thought Card
            if (step.thought) {
                const card = createStepCard("Thought (Suy nghĩ)", step.thought, "thought");
                groupDiv.appendChild(card);
            }

            // 2. Action Card
            if (step.action) {
                const card = createStepCard("Action (Hành động gọi công cụ)", `<code>${step.action}</code>`, "action");
                groupDiv.appendChild(card);
            }

            // 3. Observation Card
            if (step.observation) {
                const card = createStepCard("Observation (Kết quả trả về)", step.observation, "observation");
                groupDiv.appendChild(card);
            }

            stepsContainer.appendChild(groupDiv);
        });

        stepsContainer.scrollTop = stepsContainer.scrollHeight;
    }

    // Helper to create cards
    function createStepCard(title, content, type) {
        const card = document.createElement("div");
        card.classList.add("step-card");

        const header = document.createElement("div");
        header.classList.add("step-header", type);
        header.innerText = title;
        card.appendChild(header);

        const body = document.createElement("div");
        body.classList.add("step-content", `${type}-content`);
        body.innerHTML = content;
        card.appendChild(body);

        return card;
    }

    // Trigger actions on UI
    sendBtn.addEventListener("click", () => {
        sendMessage(chatInput.value);
    });

    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendMessage(chatInput.value);
        }
    });

    // Make suggestion buttons globally accessible
    window.sendSuggestion = function(text) {
        chatInput.value = text;
        sendMessage(text);
    };
});
