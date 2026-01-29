import React from "react";
import { X, Mail, Clock, ShieldCheck, CornerUpLeft } from "lucide-react";

export default function GmailDetailPanel({ isOpen, onClose, emailData }) {
    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop */}
            <div className="fixed inset-0 z-[100] bg-slate-950/40 backdrop-blur-sm" onClick={onClose} />
            
            {/* Slide-out Panel */}
            <div className="fixed inset-y-0 right-0 z-[101] w-full max-w-2xl border-l border-blue-500/20 bg-slate-900 shadow-[-20px_0_50px_rgba(0,0,0,0.5)] animate-in slide-in-from-right duration-500">
                <div className="flex h-full flex-col">
                    
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-slate-800 p-6 bg-slate-900/50 backdrop-blur-md">
                        <div className="flex items-center gap-4">
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600/10 text-blue-400 border border-blue-500/20">
                                <Mail size={24} />
                            </div>
                            <div>
                                <h2 className="text-lg font-bold text-white leading-tight">Email Content</h2>
                                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                                    <ShieldCheck size={12} className="text-blue-500" />
                                    WingMan Secure Sandbox
                                </p>
                            </div>
                        </div>
                        <button onClick={onClose} className="rounded-xl bg-slate-800 p-2 text-slate-400 hover:bg-rose-500/20 hover:text-rose-400 transition-all">
                            <X size={20} />
                        </button>
                    </div>

                    {/* Email Metadata Bar */}
                    <div className="bg-slate-900/80 px-8 py-4 border-b border-slate-800 flex flex-wrap gap-6 items-center">
                        <div className="flex items-center gap-2 text-xs">
                            <Clock size={14} className="text-slate-500" />
                            <span className="text-slate-400">Received:</span>
                            <span className="text-slate-200 font-medium">Fri, 23 Jan 2026</span>
                        </div>
                    </div>

                    {/* Content Area */}
                    <div className="flex-1 overflow-y-auto p-8 prose prose-invert max-w-none">
                        {/* We render the actual fetched body here instead of an iframe */}
                        <div className="rounded-3xl bg-slate-800/30 border border-slate-800 p-6 min-h-[400px]">
                            {emailData?.body || "Loading email content from WingMan Agent..."}
                        </div>
                    </div>

                    {/* Footer Actions */}
                    <div className="border-t border-slate-800 p-6 bg-slate-900/50 flex gap-3">
                        <button className="flex-1 flex items-center justify-center gap-2 rounded-2xl bg-blue-600 py-4 text-sm font-bold text-white hover:bg-blue-500 transition-all shadow-lg shadow-blue-900/20">
                            <CornerUpLeft size={18} />
                            Draft Reply
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}