import React from "react";
import { 
    MessageSquare, 
    Mail, 
    Calendar, 
    FileText, 
    Cloud, 
    Search, 
    Linkedin,
    Plus, 
    Settings, 
    X 
} from "lucide-react";

export default function Sidebar({ isOpen, toggleSidebar, activeProject, setActiveProject }) {
    const projects = [
        { 
            id: "all", 
            label: "All Sessions", 
            icon: <MessageSquare size={16} />, 
            color: "text-slate-400" 
        },
        { 
            id: "email", 
            label: "Email Agent", 
            icon: <Mail size={16} />, 
            color: "text-blue-400" 
        },
        { 
            id: "calendar", 
            label: "Calendar Agent", 
            icon: <Calendar size={16} />, 
            color: "text-purple-400" 
        },
        { 
            id: "doc", 
            label: "Doc Agent", 
            icon: <FileText size={16} />, 
            color: "text-emerald-400" 
        },
        { 
            id: "weather", 
            label: "Weather Agent", 
            icon: <Cloud size={16} />, 
            color: "text-cyan-400" 
        },
        { 
            id: "websearch", 
            label: "Web Search Agent", 
            icon: <Search size={16} />, 
            color: "text-orange-400" 
        },
        { 
            id: "linkedin", 
            label: "LinkedIn Agent", 
            icon: <Linkedin size={16} />, 
            color: "text-indigo-400" 
        },
    ];

    return (
        <>
            {/* MOBILE BACKDROP */}
            {isOpen && (
                <div 
                    className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm lg:hidden" 
                    onClick={toggleSidebar}
                />
            )}

            <aside className={`h-full bg-[#020617] border-r border-slate-800 transition-all duration-300 z-[70]
                ${isOpen ? "w-72" : "w-0"} 
                lg:relative fixed left-0 top-0 overflow-hidden`}>
                
                <div className="w-72 flex h-full flex-col p-6">
                    <div className="mb-10 flex items-center justify-between px-2">
                        <div className="flex items-center gap-3">
                            <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-900/40">
                                <MessageSquare className="text-white" size={18} />
                            </div>
                            <span className="text-sm font-black uppercase tracking-[0.3em] text-white tracking-tighter">WingMan</span>
                        </div>
                        <button onClick={toggleSidebar} className="lg:hidden text-slate-400 hover:text-white">
                            <X size={20} />
                        </button>
                    </div>

                    <button className="flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-800/50 border border-slate-700/50 py-3.5 text-xs font-bold text-slate-200 transition-all hover:bg-slate-800 hover:border-blue-500/30 mb-8">
                        <Plus size={16} />
                        <span>NEW SESSION</span>
                    </button>

                    <div className="flex-1 overflow-y-auto space-y-8 custom-scrollbar">
                        <div>
                            <p className="mb-4 px-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">Agents</p>
                            <div className="space-y-1">
                                {projects.map((p) => (
                                    <button
                                        key={p.id}
                                        onClick={() => {
                                            setActiveProject(p.id);
                                            if (window.innerWidth < 1024) toggleSidebar(); 
                                        }}
                                        className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm transition-all
                                            ${activeProject === p.id 
                                                ? "bg-blue-600/10 text-white border border-blue-500/20 shadow-lg" 
                                                : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"}`}
                                    >
                                        <span className={activeProject === p.id ? "text-blue-400" : p.color}>{p.icon}</span>
                                        <span className="font-semibold">{p.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="mt-auto pt-6 border-t border-slate-800">
                        <button className="flex w-full items-center gap-3 px-2 text-slate-500 hover:text-slate-200">
                            <Settings size={18} />
                            <span className="text-xs font-bold uppercase tracking-widest">Settings</span>
                        </button>
                    </div>
                </div>
            </aside>
        </>
    );
}