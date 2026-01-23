import { useState, useEffect, useRef } from "react";
import { nanoid } from "nanoid";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import TopBar from "../layout/TopBar";
import TypingIndicator from "./TypingIndicator";
import { useAuth } from "../../context/AuthContext";
import { loginWithGoogle } from "../../utils/auth";

export default function Chat() {
    const { isAuthenticated } = useAuth();
    const authSnapshot = useRef(isAuthenticated);
    const [historyLoaded, setHistoryLoaded] = useState(false);
    useEffect(() => {
        authSnapshot.current = isAuthenticated;
    }, [isAuthenticated]);

    useEffect(() => {
        if (!isAuthenticated || historyLoaded) return;

        async function loadHistory() {
            try {
                const res = await fetch("/history?limit=5", {
                    credentials: "include",
                });

                if (!res.ok) throw new Error("Failed to load history");

                const data = await res.json();

                const formatted = data.map((msg) => ({
                    id: nanoid(),
                    role: msg.role,
                    content: msg.content,
                    agent: msg.agent,
                }));

                setMessages(formatted);
                messagesRef.current = formatted;
                setHistoryLoaded(true);
            } catch (err) {
                console.error("History load failed:", err);
            }
        }

        loadHistory();
    }, [isAuthenticated, historyLoaded]);

    const [messages, setMessages] = useState([]);
    const messagesRef = useRef([]);

    const [isTyping, setIsTyping] = useState(false);

    async function handleSend(text) {
        if (!authSnapshot.current) {
            loginWithGoogle();
            return;
        }


        const userMessage = {
            id: nanoid(),
            role: "user",
            content: text,
        };

        setMessages((prev) => {
            const updated = [...prev, userMessage];
            messagesRef.current = updated;
            return updated;
        });
        setIsTyping(true);

        try {
            const res = await fetch("/query", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "include",
                body: JSON.stringify({ query: text }),
            });

            if (!res.ok) {
                throw new Error("Query failed");
            }

            const data = await res.json();

            const assistantMessage = {
                id: nanoid(),
                role: "assistant",
                content: data.message,
                agent: data.agent_key,
            };

            setMessages((prev) => {
                const updated = [...prev, assistantMessage];
                messagesRef.current = updated;
                return updated;
            });
        } catch (err) {
            setMessages((prev) => [
                ...prev,
                {
                    id: nanoid(),
                    role: "assistant",
                    content: "Something went wrong. Please try again.",
                },
            ]);
        } finally {
            setIsTyping(false);
        }
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
