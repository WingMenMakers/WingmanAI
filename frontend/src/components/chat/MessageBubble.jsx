console.log("MessageBubble rendered");

export default function MessageBubble({ role, content }) {
    const isUser = role === "user";

    
    return (
        <div
            className={`w-full flex ${isUser ? "justify-end" : "justify-start"}`}
        >
            <div
                className={`
          max-w-[70%] px-4 py-2 rounded-lg
          ${isUser
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800 text-gray-100"}
        `}
            >
                {content}
            </div>
        </div>
    );
}
