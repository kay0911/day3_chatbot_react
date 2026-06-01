document.addEventListener("DOMContentLoaded", () => {
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const chatMessages = document.getElementById("chat-messages");
    const stepsContainer = document.getElementById("steps-container");
    const emptyTelemetry = document.getElementById("empty-telemetry");

    let chatHistory = [];

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
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: text,
                    history: chatHistory
                })
            });

            if (!response.ok) {
                throw new Error("Không thể kết nối đến Web Server.");
            }

            const data = await response.json();
            
            // Remove typing indicator
            typingIndicator.remove();

            // Render Final Answer
            if (data.answer) {
                appendMessage(data.answer, "assistant");
                
                // Lưu vào lịch sử hội thoại trong phiên (Session Memory)
                chatHistory.push({ role: "user", content: text });
                chatHistory.push({ role: "assistant", content: data.answer });
                
                // Giới hạn bộ nhớ chỉ lưu 10 tin nhắn gần nhất để tránh phồng token
                if (chatHistory.length > 10) {
                    chatHistory.splice(0, 2);
                }
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
            appendMessage(`❌ Lỗi: ${error.message}. Hãy chắc chắn rằng Web Server đang chạy tại cổng 5000.`, "assistant");
            emptyTelemetry.style.display = "flex";
        }
    }

    // Append standard message in chat bubbles
    function appendMessage(text, sender) {
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
        } else {
            messageDiv.innerText = text;
        }

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Simple markdown compiler for chat representation
    function formatMarkdown(text) {
        let html = text;
        
        // Escape HTML
        html = html
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

        // Unordered list
        html = html.replace(/^\s*-\s+(.*)$/gm, "<li>$1</li>");
        html = html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

        // Ordered list
        html = html.replace(/^\s*(\d+)\.\s+(.*)$/gm, "<li>$2</li>");
        html = html.replace(/(<li>.*<\/li>)/s, "<ol>$1</ol>");

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
        body.classList.add("step-content");
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
