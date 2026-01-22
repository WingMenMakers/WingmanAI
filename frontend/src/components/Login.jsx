import API from "../config"

export default function Login() {
    return (
        <div className="min-h-screen flex items-center justify-center">
            <div className="p-6 rounded bg-gray-800 text-white">
                <h1 className="text-xl mb-4">Welcome to WingMan</h1>

                <a
                    href={`${API}/login/google`}
                    className="px-4 py-2 bg-blue-600 rounded"
                >
                    Sign in with Google
                </a>
            </div>
        </div>
    )
}
