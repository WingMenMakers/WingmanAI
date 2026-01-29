import React, { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";

export default function SplashScreen({ onComplete }) {
    const [status, setStatus] = useState("Initializing...");

    useEffect(() => {
        const sequence = [
            { text: "Establishing secure link...", delay: 800 },
            { text: "Loading Knowledge Graph...", delay: 1500 },
            { text: "Syncing with WingMan AI...", delay: 2200 },
            { text: "READY", delay: 2800 },
        ];

        sequence.forEach((step, i) => {
            setTimeout(() => setStatus(step.text), step.delay);
        });

        setTimeout(onComplete, 3500);
    }, [onComplete]);

    return (
        <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[#020617]">
            {/* Pulsing Logo */}
            <div className="relative mb-8">
                <div className="absolute inset-0 animate-ping rounded-3xl bg-blue-500/20" />
                <div className="relative flex h-24 w-24 items-center justify-center rounded-[2.5rem] border border-blue-500/30 bg-blue-600/10 shadow-[0_0_50px_rgba(37,99,235,0.2)]">
                    <Sparkles className="text-blue-500 animate-pulse" size={48} />
                </div>
            </div>

            {/* Matrix Loading Text */}
            <div className="flex flex-col items-center gap-2">
                <h1 className="text-2xl font-bold tracking-[0.2em] text-white uppercase">WingMan AI</h1>
                <div className="flex items-center gap-2 text-blue-500/60 font-mono text-xs uppercase tracking-widest">
                    <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                    {status}
                </div>
            </div>
        </div>
    );
}