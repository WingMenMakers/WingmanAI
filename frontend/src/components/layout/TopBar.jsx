import React, { useState } from "react";
import { Menu, Sparkles, ChevronDown, Bell, LogOut, Settings, Activity } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { loginWithGoogle } from "../../utils/auth";

export default function TopBar({ onToggleSidebar, isSidebarOpen }) {
    const { user, logout } = useAuth();
    const [open, setOpen] = useState(false);

    return (
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-800 bg-[#020617]/80 px-6 backdrop-blur-md z-30">
            <div className="flex items-center gap-4">
                {/* Sidebar Toggle */}
                <button 
                    onClick={onToggleSidebar}
                    className="flex h-10 w-10 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white transition-all active:scale-95"
                >
                    <Menu size={22} />
                </button>

                {/* Responsive Branding */}
                <div className={`flex items-center gap-2 transition-opacity duration-300 
                    ${isSidebarOpen ? "lg:opacity-0 lg:pointer-events-none" : "opacity-100"}`}>
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 shadow-lg shadow-blue-500/20">
                        <Sparkles className="text-white" size={18} />
                    </div>
                    <span className="text-sm font-black uppercase tracking-[0.2em] text-white hidden sm:block">
                        WingMan
                    </span>
                </div>
            </div>

            {/* Right Side Actions */}
            <div className="flex items-center gap-3">
                <button className="hidden sm:flex h-9 w-9 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 transition-colors">
                    <Bell size={18} />
                </button>
                
                <div className="h-8 w-px bg-slate-800 mx-1 hidden sm:block" />

                {user ? (
                    <div className="relative">
                        <button 
                            onClick={() => setOpen(!open)}
                            className={`group flex items-center gap-2 rounded-full p-1 pr-3 transition-all border
                                ${open 
                                    ? "bg-slate-800 border-slate-700" 
                                    : "bg-slate-900/50 border-slate-800 hover:border-slate-700 hover:bg-slate-800/50"
                                }`}
                        >
                            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-indigo-900/20 text-[11px] font-bold text-white uppercase overflow-hidden">
                                {user?.name?.[0]?.toUpperCase() || "A"}
                            </div>
                            
                            <ChevronDown 
                                size={14} 
                                className={`text-slate-500 transition-transform duration-300 
                                    ${open ? "rotate-180 text-blue-400" : "group-hover:text-slate-300"}`} 
                            />
                        </button>

                        {open && (
                            <div className="absolute right-0 mt-3 w-56 origin-top-right overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                                <div className="border-b border-slate-800 bg-slate-800/30 px-4 py-3">
                                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Account</p>
                                    <p className="mt-0.5 truncate text-sm font-medium text-slate-200">{user?.name || "User"}</p>
                                </div>
                                
                                <div className="p-1.5">
                                    <button className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition">
                                        <Settings size={15}/> <span>Preferences</span>
                                    </button>
                                    <button className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition">
                                        <Activity size={15}/> <span>Usage Stats</span>
                                    </button>
                                    
                                    <div className="my-1 border-t border-slate-800" />
                                    
                                    <button
                                        onClick={logout}
                                        className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm font-medium text-rose-400 hover:bg-rose-500/10 transition"
                                    >
                                        <LogOut size={15} /> Sign Out
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <button
                        onClick={loginWithGoogle}
                        className="flex h-9 items-center rounded-full bg-slate-800 px-4 text-sm font-medium text-slate-100 shadow hover:bg-slate-700 transition"
                    >
                        Sign in
                    </button>
                )}
            </div>
        </header>
    );
}