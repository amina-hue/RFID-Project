import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { ping } from "../api";
import "./layout.css";

const TITRES = {
  "/journal": ["Journal des accès", "Entrées dans les salles de TP, refus inclus"],
  "/statistiques": ["Statistiques", "Fréquentation des salles"],
  "/utilisateurs": ["Utilisateurs et badges", "Gestion des comptes et des badges"],
  "/salles": ["Salles et autorisations", "Qui peut entrer dans quelle salle"],
};

export default function AppLayout() {
  const [theme, setTheme] = useState("dark");
  const [online, setOnline] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => {
    const test = () => ping().then(() => setOnline(true)).catch(() => setOnline(false));
    test();
    const id = setInterval(test, 10000);
    return () => clearInterval(id);
  }, []);

  const [title, subtitle] = TITRES[pathname] || ["UniAccess", ""];

  return (
    <div className="app" data-theme={theme}>
      <Sidebar />
      <div className="app__main">
        <Topbar
          title={title}
          subtitle={subtitle}
          online={online}
          theme={theme}
          onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
        />
        <main className="app__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
