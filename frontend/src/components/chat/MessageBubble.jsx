import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { User, Sparkles, Copy, Check, Cpu, Mail, ExternalLink } from "lucide-react";

export default function MessageBubble({ role, content, agent, timestamp, onOpenMail }) {
    const isAi = role === "assistant";
    const [copied, setCopied] = useState(false);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const renderContent = (text) => {
        const emailRegex = /\d+\.\s\*\*Sender:\*\*\s(.*?)\s+\*\*Subject:\*\*\s(.*?)\s+\*\*Date:\*\*\s(.*?)(?=\n\d+\.|$)/gs;
        const parts = [];
        let lastIndex = 0;
        let match;

        while ((match = emailRegex.exec(text)) !== null) {
            parts.push(<ReactMarkdown key={`text-${match.index}`}>{text.substring(lastIndex, match.index)}</ReactMarkdown>);
            
            const [_, sender, subject, date] = match;
            parts.push(
                <div key={`card-${match.index}`} className="my-5 overflow-hidden rounded-2xl border border-slate-700/50 bg-slate-800/30 backdrop-blur-sm transition-all hover:border-blue-500/40 hover:bg-slate-800/50 group/card shadow-lg shadow-black/20">
                    <div className="flex items-center justify-between p-4 sm:p-5">
                        <div className="flex items-center gap-4 min-w-0">
                            {/* Icon with Brand Glow */}
                            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 group-hover/card:scale-110 transition-transform">
                                <Mail size={22} />
                            </div>
                            
                            <div className="min-w-0">
                                <h4 className="truncate text-[15px] font-bold text-slate-100 mb-0.5 tracking-tight">{subject}</h4>
                                <p className="truncate text-xs font-medium text-slate-400 flex items-center gap-1.5">
                                    <span className="opacity-50 font-bold uppercase text-[9px]">From:</span> {sender}
                                </p>
                                <div className="mt-2 flex items-center gap-2">
                                    <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest bg-slate-900/50 px-2 py-0.5 rounded">
                                        {date}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Trigger the Slide-out Panel */}
                        <button 
                            onClick={() => onOpenMail(subject)} 
                            className="ml-4 flex h-10 items-center gap-2 rounded-xl bg-slate-900 px-4 text-xs font-bold text-slate-300 transition-all hover:bg-blue-600 hover:text-white border border-slate-700/50"
                        >
                            <span>OPEN</span>
                            <ExternalLink size={14} />
                        </button>
                    </div>
                </div>
            );
            lastIndex = emailRegex.lastIndex;
        }
        
        if (lastIndex < text.length) {
            parts.push(<ReactMarkdown key="text-end">{text.substring(lastIndex)}</ReactMarkdown>);
        }
        
        return parts.length > 0 ? parts : <ReactMarkdown>{text}</ReactMarkdown>;
    };

    return (
        <div className={`group w-full py-6 transition-colors ${isAi ? "bg-slate-900/30" : "bg-transparent"}`}>
            <div className={`mx-auto flex max-w-4xl w-full gap-4 md:gap-6 px-4 ${isAi ? "flex-row" : "flex-row-reverse"}`}>
                
                {/* Avatar with Glow Track */}
                <div className={`relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border transition-all duration-300
                    ${isAi ? "border-blue-500/30 bg-blue-600/10 text-blue-400" : "border-slate-700 bg-slate-800 text-slate-300"}`}>
                    {isAi ? <Sparkles size={18} strokeWidth={2.5} className="animate-pulse" /> : <User size={18} />}
                    {/* Glow Track Line */}
                    {isAi && <div className="absolute top-10 bottom-[-100px] w-[1px] bg-gradient-to-b from-blue-500/20 to-transparent" />}
                </div>

                {/* Body Content */}
                <div className={`flex flex-col min-w-0 max-w-[85%] ${isAi ? "items-start" : "items-end"}`}>
                    <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] font-extrabold uppercase tracking-widest text-slate-500">
                            {isAi ? "WingMan AI" : "You"}
                        </span>
                        {isAi && (
                            <div className="flex items-center gap-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 px-2.5 py-0.5">
                                <Cpu size={10} className="text-blue-400" />
                                <span className="text-[9px] font-bold text-blue-400 uppercase tracking-tighter">
                                    {agent || "GMAIL_AGENT"}
                                </span>
                            </div>
                        )}
                    </div>

                    <div className={`relative rounded-3xl px-6 py-5 text-[15px] leading-relaxed antialiased transition-all duration-300
                        ${isAi 
                            ? "text-slate-200 bg-slate-800/40 border border-slate-700/50 backdrop-blur-md shadow-[0_0_20px_rgba(59,130,246,0.03)]" 
                            : "bg-blue-600 text-white shadow-lg shadow-blue-900/20"}`}>
                        
                        <div className="prose prose-invert max-w-none">
                            {renderContent(content)}
                        </div>

                        {isAi && (
                            <div className="mt-4 flex items-center pt-4 border-t border-slate-700/40">
                                <button onClick={copyToClipboard} className="flex items-center gap-2 text-[10px] font-bold text-slate-500 hover:text-blue-400 transition-colors uppercase tracking-widest">
                                    {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
                                    <span>{copied ? "COPIED" : "COPY"}</span>
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}