import React, { useState, useEffect } from "react";
import { Sparkles, Cpu, Layers, Terminal } from "lucide-react";

export default function TypingIndicator() {
    const [statusIndex, setStatusIndex] = useState(0);
    
    // Generic multi-agent workflow steps
    const steps = [
        { label: "Director: Analyzing Intent", icon: <Cpu size={12} /> },
        { label: "Director: Routing to Agent", icon: <Layers size={12} /> },
        { label: "Agent: Processing Request", icon: <Terminal size={12} /> },
        { label: "Director: Formatting Response", icon: <Sparkles size={12} /> }
    ];

    useEffect(() => {
        const interval = setInterval(() => {
            setStatusIndex((prev) => (prev + 1) % steps.length);
        }, 1500);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="w-full py-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="mx-auto flex max-w-4xl w-full gap-4 md:gap-6 px-4">
                
                {/* Pulsing Avatar */}
                <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-blue-500/30 bg-blue-600/10 text-blue-400">
                    <Sparkles size={18} strokeWidth={2.5} className="animate-pulse" />
                    <div className="absolute inset-0 rounded-xl bg-blue-500/20 animate-ping opacity-20" />
                </div>

                {/* Status Badge */}
                <div className="flex flex-col items-start gap-3">
                    <div className="flex items-center gap-2 rounded-full bg-slate-900/80 border border-slate-800 px-4 py-2 shadow-2xl backdrop-blur-md">
                        <div className="flex items-center justify-center text-blue-500 animate-pulse">
                            {steps[statusIndex].icon}
                        </div>
                        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-300">
                            {steps[statusIndex].label}
                        </span>
                    </div>
                    
                    {/* Animated Loading Bar */}
                    <div className="ml-2 flex gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-bounce [animation-delay:-0.3s]"></span>
                        <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-bounce [animation-delay:-0.15s]"></span>
                        <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-bounce"></span>
                    </div>
                </div>
            </div>
        </div>
    );
}