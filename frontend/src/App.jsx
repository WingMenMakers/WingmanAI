// src/App.jsx
import { AuthProvider } from "./context/AuthContext";
import Chat from "./components/chat/Chat";

export default function App() {
  return (
    <AuthProvider>
      <Chat />
    </AuthProvider>
  );
}
