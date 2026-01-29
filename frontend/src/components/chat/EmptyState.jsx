import React from "react";
import { Mail, Calendar, Search, FileText, Sparkles } from "lucide-react";

export default function EmptyState({ onActionClick }) {
    const suggestions = [
        { 
            title: "Manage Mails", 
            desc: "Summarize recent emails or draft a reply.", 
            icon: <Mail size={20} className="text-blue-400" />,
            prompt: "Summarize my last 5 emails from Gmail."
        },
        { 
            title: "Search Web", 
            desc: "Get real-time answers with the Search Agent.", 
            icon: <Search size={20} className="text-indigo-400" />,
            prompt: "What are the top tech news stories today?"
        },
        { 
            title: "Docs & Calendar", 
            desc: "Create docs or check your schedule.", 
            icon: <Calendar size={20} className="text-emerald-400" />,
            prompt: "What is on my schedule for tomorrow?"
        }
    ];

    return (
        <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
            <div className="mb-8 relative">
                <div className="absolute inset-0 animate-ping rounded-full bg-blue-500/10" />
                <div className="relative flex h-20 w-20 items-center justify-center rounded-[2.5rem] bg-blue-600/10 border border-blue-500/20 shadow-2xl">
                    <Sparkles className="text-blue-500" size={40} />
                </div>
            </div>
            
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">
                How can WingMan assist you?
            </h1>
            <p className="max-w-md text-slate-400 text-lg mb-12">
                I can orchestrate tasks across your Gmail, Docs, and Web Search.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-5xl">
                {suggestions.map((item, idx) => (
                    <button
                        key={idx}
                        onClick={() => onActionClick(item.prompt)}
                        className="flex flex-col items-start p-6 rounded-3xl bg-slate-900/50 border border-slate-800/80 hover:border-blue-500/50 hover:bg-slate-800/40 transition-all duration-300 text-left group"
                    >
                        <div className="mb-4 p-3 rounded-2xl bg-slate-800 group-hover:bg-blue-600/10 transition-colors">
                            {item.icon}
                        </div>
                        <h3 className="text-slate-100 font-bold mb-1">{item.title}</h3>
                        <p className="text-slate-500 text-xs leading-relaxed">{item.desc}</p>
                    </button>
                ))}
            </div>
        </div>
    );
}