import { useState, useEffect, useRef } from "react";
import { nanoid } from "nanoid";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import TypingIndicator from "./TypingIndicator";
import TopBar from "../layout/TopBar";
import EmptyState from "./EmptyState";
import SplashScreen from "../layout/SplashScreen";
import GmailDetailPanel from "../layout/GmailDetailPanel";
import Sidebar from "../layout/Sidebar";
import FullScreenLoader from "../FullScreenLoader";
import Login from "../Login";
import { useAuth } from "../../context/AuthContext";
import { loginWithGoogle } from "../../utils/auth";

export default function Chat() {
    const { isAuthenticated, loading } = useAuth();
    
    const [showSplash, setShowSplash] = useState(true);
    const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth > 1024); 
    const [activeProject, setActiveProject] = useState("all");
    const [isPanelOpen, setIsPanelOpen] = useState(false);
    const [panelData, setPanelData] = useState(null);
    const [messages, setMessages] = useState([]);
    const [isTyping, setIsTyping] = useState(false);
    const scrollContainerRef = useRef(null);

    useEffect(() => {
        if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTo({
                top: scrollContainerRef.current.scrollHeight,
                behavior: "smooth",
            });
        }
    }, [messages, isTyping]);

    const openMailPanel = async (emailId) => {
        setIsPanelOpen(true);
        setPanelData(null); 
        try {
            const res = await fetch(`/api/email-detail/${emailId}`);
            const data = await res.json();
            setPanelData(data);
        } catch (err) {
            setPanelData({ body: "Error retrieving content from WingMan Agent." });
        }
    };

    async function handleSend(text) {
        if (!isAuthenticated) {
            loginWithGoogle();
            return;
        }

        const userMessage = { id: nanoid(), role: "user", content: text };
        setMessages((prev) => [...prev, userMessage]);
        setIsTyping(true);

        try {
            const res = await fetch("/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ query: text, project: activeProject }),
            });
            const data = await res.json();
            
            setMessages((prev) => [...prev, { 
                id: nanoid(), 
                role: "assistant", 
                content: data.message,
                agent: data.agent_key 
            }]);
        } catch (err) {
            console.error(err);
            setMessages((prev) => [...prev, { id: nanoid(), role: "assistant", content: "System error." }]);
        } finally {
            setIsTyping(false);
        }
    }

    if (loading) return <FullScreenLoader />;
    if (!isAuthenticated) return <Login />;
    if (showSplash) return <SplashScreen onComplete={() => setShowSplash(false)} />;

    return (
        <div className="flex h-screen w-full overflow-hidden bg-[#020617] text-slate-100">
            <Sidebar 
                isOpen={isSidebarOpen} 
                toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} 
                activeProject={activeProject}
                setActiveProject={setActiveProject}
            />

            <div className="relative flex flex-col flex-1 h-full min-w-0">
                <TopBar 
                    onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} 
                    isSidebarOpen={isSidebarOpen}
                />

                <main ref={scrollContainerRef} className="flex-1 overflow-y-auto overflow-x-hidden scroll-smooth">
                    {/* pb-80: Increased padding to ensure cards/messages clear the gradient 
                        transition-all: Matches sidebar/panel movement
                    */}
                    <div className={`flex flex-col pb-80 pt-8 transition-all duration-500 
                        ${isPanelOpen ? "lg:mr-[500px]" : "mr-0"}`}>
                        {messages.length === 0 ? (
                            <EmptyState onActionClick={handleSend} />
                        ) : (
                            <>
                                <MessageList messages={messages} onOpenMail={openMailPanel} />
                                {isTyping && <TypingIndicator />}
                            </>
                        )}
                    </div>
                </main>

                {/* THE FLOATING INPUT LAYER: Fixed to the bottom of the content lane */}
                <div className="absolute bottom-0 left-0 w-full z-20 pointer-events-none">
                    
                    {/* The Gradient Fade: Taller (h-48) to prevent sharp text cutting */}
                    <div className="h-48 w-full bg-gradient-to-t from-[#020617] via-[#020617]/90 to-transparent backdrop-blur-[2px]" />
                    
                    {/* The Solid Base: Houses the actual interactive elements */}
                    <div className="bg-[#020617] pb-6 pointer-events-auto">
                        <ChatInput onSend={handleSend} />
                        
                        {/* Status/Branding Track */}
                        <div className="mt-4 flex items-center justify-center gap-4 opacity-30 select-none">
                            <div className="h-[1px] w-16 bg-gradient-to-r from-transparent via-slate-500 to-transparent" />
                            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">
                                Orchestrator v2.0
                            </p>
                            <div className="h-[1px] w-16 bg-gradient-to-r from-transparent via-slate-500 to-transparent" />
                        </div>
                    </div>
                </div>
            </div>

            <GmailDetailPanel 
                isOpen={isPanelOpen} 
                onClose={() => setIsPanelOpen(false)} 
                emailData={panelData} 
            />
        </div>
    );
}