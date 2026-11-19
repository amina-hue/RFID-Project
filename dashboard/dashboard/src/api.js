// Adresse de l'API : modifiable avec VITE_API_URL dans un fichier .env
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function req(path, options) {
  const r = await fetch(BASE + path, options);
  const data = await r.json().catch(() => null);
  if (!r.ok) throw new Error(data?.detail || `Erreur ${r.status}`);
  return data;
}

export const ping = () => req("/");
export const getAcces = () => req("/statistiques/derniers-acces?limite=500&jours=30");
export const getSalles = () => req("/salles");
export const getUtilisateurs = () => req("/utilisateurs");
export const autoriserManuellement = (body) =>
  req("/acces/manuel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
