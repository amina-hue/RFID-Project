import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./layout/AppLayout";
import Journal from "./pages/Journal";
import JournalProf from "./pages/JournalProf";
import Placeholder from "./pages/Placeholder";

export default function App() {
  return (
    <Routes>
      {/* Vue enseignant : page seule, sans sidebar */}
      <Route path="prof" element={<JournalProf />} />

      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/journal" replace />} />
        <Route path="journal" element={<Journal />} />
        {["statistiques", "utilisateurs", "salles"].map((p) => (
          <Route key={p} path={p} element={<Placeholder />} />
        ))}
      </Route>
    </Routes>
  );
}