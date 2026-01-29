import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

export default function MessageList({ messages, onOpenMail }) { // 1. Receive it here
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    return (
        <div className="flex flex-col gap-2">
            {messages.map((msg) => (
                <MessageBubble
                    key={msg.id || `${msg.role}-${msg.content}`}
                    role={msg.role}
                    content={msg.content}
                    agent={msg.agent}
                    onOpenMail={onOpenMail} // 2. Pass it here
                />
            ))}
            <div ref={bottomRef} />
        </div>
    );
}