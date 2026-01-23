import { useState } from "react"; 
import { useAuth } from "../../context/AuthContext";
import { loginWithGoogle } from "../../utils/auth";

export default function TopBar() {
    const { user, loading, logout } = useAuth();
    const [open, setOpen] = useState(false);

    if (loading) {
        return (
            <div className="h-14 flex items-center justify-end px-4">
                <div className="h-8 w-8 rounded-full bg-slate-700 animate-pulse" />
            </div>
        );
    }

    return (
        <div className="h-14 flex items-center justify-between px-6">
            <div className="text-lg font-semibold">WingMan</div>

            {/* Badge */}
            {user ? (
                <div className="relative">
                    <button
                        onClick={() => setOpen((v) => !v)}
                        className="h-8 w-8 rounded-full bg-indigo-600 flex items-center justify-center"
                    >
                        {user.name?.[0]?.toUpperCase() || "U"}
                    </button>

                    {open && (
                        <div className="absolute right-0 mt-2 w-40 rounded-lg bg-slate-900 border border-slate-800">
                            <button
                                onClick={logout}
                                className="w-full px-4 py-2 text-left hover:bg-slate-800"
                            >
                                Logout
                            </button>
                        </div>
                    )}
                </div>
            ) : (
                <button
                    onClick={loginWithGoogle}
                    className="h-8 w-8 rounded-full bg-slate-700 flex items-center justify-center hover:bg-slate-600 transition"
                    title="Sign in"
                >
                    A
                </button>
            )}
        </div>
    );
}