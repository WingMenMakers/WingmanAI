export default function TopBar() {
    return (
        <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
            <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-4">

                {/* App name / logo */}
                <h1 className="text-sm font-semibold tracking-wide text-white">
                    WingMan
                </h1>

                {/* User avatar */}
                <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-700 text-xs font-medium text-white">
                        A
                    </div>
                </div>
            </div>
        </header>
    );
}
