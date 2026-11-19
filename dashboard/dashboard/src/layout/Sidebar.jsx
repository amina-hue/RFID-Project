import { NavLink } from "react-router-dom";
import {
  LayoutGrid,
  FileText,
  BarChart3,
  UserSquare2,
  DoorOpen,
  ShieldCheck,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Vue d’ensemble", icon: LayoutGrid, end: true },
  { to: "/journal", label: "Journal", icon: FileText },
  { to: "/statistiques", label: "Statistiques", icon: BarChart3 },
  { to: "/utilisateurs", label: "Utilisateurs et badges", icon: UserSquare2 },
  { to: "/salles", label: "Salles et autorisations", icon: DoorOpen },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo">
          <ShieldCheck size={20} />
        </div>
        <div>
          <div className="sidebar__name">UniAccess</div>
          <div className="sidebar__tag">CONTRÔLE RFID</div>
        </div>
      </div>

      <nav className="sidebar__nav">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              "sidebar__link" + (isActive ? " is-active" : "")
            }
          >
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar__footer">
        <div className="sidebar__campus">
          <div className="sidebar__campus-logo">U</div>
          <div>
            <div className="sidebar__campus-name">Université Lumière</div>
            <div className="sidebar__campus-sub">Campus Sciences</div>
          </div>
        </div>
        <div className="sidebar__version">Version 2.4.0</div>
      </div>
    </aside>
  );
}
