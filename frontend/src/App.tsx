import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { AgentDashboard } from "./pages/AgentDashboard";
import { TicketQueue } from "./pages/TicketQueue";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 px-6 py-2 flex gap-6 items-center">
          <div className="flex items-center gap-2 mr-4">
            <div className="w-6 h-6 bg-orange-500 rounded flex items-center justify-center text-white text-xs font-bold">स</div>
            <span className="font-bold text-sm text-gray-900">Sahayak AI</span>
          </div>
          <NavLink
            to="/"
            className={({ isActive }) =>
              `text-sm font-medium pb-2 border-b-2 ${isActive ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-800"}`
            }
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/queue"
            className={({ isActive }) =>
              `text-sm font-medium pb-2 border-b-2 ${isActive ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-800"}`
            }
          >
            Queue
          </NavLink>
        </nav>

        <div className="pt-12">
          <Routes>
            <Route path="/" element={<AgentDashboard />} />
            <Route path="/queue" element={<TicketQueue />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
