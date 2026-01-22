import { useState } from "react";
import { nanoid } from "nanoid";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import TopBar from "../layout/TopBar";
import TypingIndicator from "./TypingIndicator";

export default function Chat() {
    const [messages, setMessages] = useState([
        {
            id: nanoid(),
            role: "user",
            content: "Can you check my inbox for new emails?",
        },
        {
            id: nanoid(),
            role: "assistant",
            content: "Sure — here are your latest 5 emails.",
        },
    ]);

    const [isTyping, setIsTyping] = useState(false);

    function handleSend(text) {
        const userMessage = {
            id: nanoid(),
            role: "user",
            content: text,
        };

        setMessages((prev) => [...prev, userMessage]);

        // Simulate assistant typing
        setIsTyping(true);

        setTimeout(() => {
            const assistantMessage = {
                id: nanoid(),
                role: "assistant",
                content: "This is a simulated reply. Backend comes next.",
            };

            setMessages((prev) => [...prev, assistantMessage]);
            setIsTyping(false);
        }, 1000);
    }

    return (
        <div className="flex h-screen w-screen flex-col bg-slate-950 text-white">
            <TopBar />

            <div className="flex-1 flex justify-center overflow-y-auto">
                <div className="w-full max-w-3xl px-6 py-8 flex flex-col">
                    <div className="flex-1 space-y-6">
                        <MessageList messages={messages} />
                        {isTyping && <TypingIndicator />}
                    </div>

                    <div className="pt-6">
                        <ChatInput onSend={handleSend} />
                    </div>
                </div>
            </div>
        </div>
    );
}
