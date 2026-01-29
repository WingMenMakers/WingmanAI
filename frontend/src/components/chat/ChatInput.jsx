import { useEffect, useRef, useState } from "react";
import { Plus, Globe } from "lucide-react";

export default function ChatInput({ onSend }) {
    const [text, setText] = useState("");
    const [isFocused, setIsFocused] = useState(false);
    const textareaRef = useRef(null);

    useEffect(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.style.height = "auto";
        el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    }, [text]);

    function handleSubmit(e) {
        if (e) e.preventDefault();
        if (!text.trim()) return;
        onSend(text.trim()); 
        setText("");
    }

    const handleKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className="mx-auto w-full max-w-3xl px-4 pb-6">
            <form
                onSubmit={handleSubmit}
                className={`group relative flex flex-col transition-all duration-200
                    rounded-3xl border bg-slate-900/60 backdrop-blur-xl
                    ${isFocused 
                        ? "border-blue-500/50 shadow-[0_0_20px_rgba(59,130,246,0.15)] ring-1 ring-blue-500/20" 
                        : "border-slate-800/80 shadow-xl shadow-black/20"}`}
            >
                <div className="flex items-start px-4 pt-4">
                    <textarea
                        ref={textareaRef}
                        rows={1}
                        value={text}
                        onFocus={() => setIsFocused(true)}
                        onBlur={() => setIsFocused(false)}
                        onKeyDown={handleKeyDown}
                        onChange={(e) => setText(e.target.value)}
                        placeholder="Ask WingMan anything..."
                        className="w-full resize-none bg-transparent pt-1 text-[15px] text-slate-100 placeholder:text-slate-500 outline-none min-h-[40px] leading-6"
                    />
                </div>

                <div className="flex items-center justify-between px-3 pb-3 pt-2">
                    <div className="flex items-center gap-1">
                        <button type="button" className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition-colors">
                            <Plus size={18} />
                        </button>
                        <button type="button" className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition-colors">
                            <Globe size={18} />
                        </button>
                    </div>

                    <div className="flex items-center gap-3">
                        <span className="text-[11px] font-medium text-slate-500 hidden sm:block">
                            Shift + Enter for new line
                        </span>
                        <button
                            type="submit"
                            disabled={!text.trim()}
                            className={`flex h-9 w-9 items-center justify-center rounded-full transition-all duration-200
                                ${text.trim() 
                                    ? "bg-blue-600 text-white shadow-lg hover:scale-105 hover:bg-blue-500 active:scale-95" 
                                    : "bg-slate-800 text-slate-600 cursor-not-allowed"}`}
                        >
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                <path d="M12 19V5M5 12l7-7 7 7"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </form>
        </div>
    );
}