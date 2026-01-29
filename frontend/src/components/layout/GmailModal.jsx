import React, { useEffect } from "react";
import { X, ExternalLink, ShieldCheck } from "lucide-react";

export default function GmailModal({ isOpen, onClose, url, title }) {
    // Handle "Esc" key to close
    useEffect(() => {
        const handleEsc = (e) => {
            if (e.key === "Escape") onClose();
        };
        window.addEventListener("keydown", handleEsc);
        return () => window.removeEventListener("keydown", handleEsc);
    }, [onClose]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 md:p-10">
            {/* Backdrop Blur */}
            <div 
                className="absolute inset-0 bg-slate-950/60 backdrop-blur-md animate-in fade-in duration-300" 
                onClick={onClose} 
            />

            {/* Modal Container */}
            <div className="relative flex h-full w-full max-w-6xl flex-col overflow-hidden rounded-3xl border border-blue-500/30 bg-slate-900 shadow-[0_0_50px_rgba(37,99,235,0.2)] animate-in zoom-in-95 duration-300">
                
                {/* Header Area */}
                <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/50 px-6 py-4 backdrop-blur-md">
                    <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400">
                            <ShieldCheck size={20} />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-white uppercase tracking-tight">{title || "Secure View"}</h3>
                            <p className="text-[10px] font-medium text-slate-500 uppercase tracking-widest">WingMan Sandboxed Environment</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <button 
                            onClick={() => window.open(url, '_blank')}
                            className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
                            title="Open in new tab"
                        >
                            <ExternalLink size={18} />
                        </button>
                        <button 
                            onClick={onClose}
                            className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800 text-slate-400 hover:bg-rose-500/20 hover:text-rose-400 transition-all"
                        >
                            <X size={20} />
                        </button>
                    </div>
                </div>

                {/* The Iframe / Loading State */}
                <div className="relative flex-1 bg-white">
                    {/* Brand Loading Overlay */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900 pointer-events-none animate-out fade-out fill-mode-forwards delay-1000">
                        <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-blue-500/20 border-t-blue-500" />
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-[0.2em] animate-pulse">
                            WingMan is retrieving your mail...
                        </p>
                    </div>

                    <iframe 
                        src={url} 
                        className="h-full w-full border-none"
                        title="Gmail Content"
                    />
                </div>
            </div>
        </div>
    );
}