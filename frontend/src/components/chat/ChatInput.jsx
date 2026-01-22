import { useState } from "react";

export default function ChatInput({ onSend }) {
    const [text, setText] = useState("");

    function handleSubmit(e) {
        e.preventDefault();
        if (!text.trim()) return;
        onSend(text);
        setText("");
    }

    return (
        <form
            onSubmit={handleSubmit}
            className="flex items-center gap-3 rounded-xl bg-slate-900 px-4 py-3 shadow-lg"
        >
            <input
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Ask WingMan anything..."
                className="flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-400"
            />
            <button
                type="submit"
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
            >
                Send
            </button>
        </form>
    );
}
