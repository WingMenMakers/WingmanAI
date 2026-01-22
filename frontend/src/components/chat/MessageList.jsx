import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

export default function MessageList({ messages }) {
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    return (
        <div className="space-y-4">
            {messages.map((msg, id) => (
                <MessageBubble
                    key={id}
                    role={msg.role}
                    content={msg.content}
                />
            ))}

            {/* Scroll anchor */}
            <div ref={bottomRef} />
        </div>
    );
}
