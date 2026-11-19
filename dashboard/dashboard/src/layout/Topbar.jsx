import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

function useClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export default function Topbar({
  title,
  subtitle,
  online = true,
  readers = null,
  theme = "dark",
  onToggleTheme,
}) {
  const now = useClock();
  const time = now.toLocaleTimeString("fr-FR");
  const date = now.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  return (
    <header className="topbar">
      <div className="topbar__titles">
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>

      <div className="topbar__right">
        <div className="topbar__status">
          <span className={"topbar__dot" + (online ? "" : " is-off")} />
          <div>
            <div className="topbar__status-main">
              {online ? "Système en ligne" : "Système hors ligne"}
            </div>
            <div className="topbar__status-sub">
              {!online ? "API injoignable" : readers != null ? `${readers} lecteurs connectés` : "API connectée"}
            </div>
          </div>
        </div>

        <div className="topbar__clock">
          <div className="topbar__time">{time}</div>
          <div className="topbar__date">{date}</div>
        </div>

        <button
          className="topbar__theme"
          onClick={onToggleTheme}
          aria-label="Changer de thème"
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </header>
  );
}
