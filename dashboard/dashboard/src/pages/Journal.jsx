import { useCallback, useEffect, useMemo, useState } from "react";
import { getAcces, getSalles, getUtilisateurs, autoriserManuellement } from "../api";
import "./journal.css";

const RAISONS = {
  badge_inconnu: "badge inconnu",
  badge_revoque: "badge révoqué",
  salle_non_autorisee: "salle non autorisée",
  hors_periode: "hors période",
  salle_inconnue: "salle inconnue",
  erreur_interne: "erreur interne",
};
const STATUTS = {
  autorise: ["Autorisé", "ok"],
  refuse: ["Refusé", "ko"],
  manuel: ["Manuel", "man"],
};

const pad = (n) => String(n).padStart(2, "0");
const jour = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const heure = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;
const initial = () => ({ salle: "", date: jour(new Date()), de: "", a: "", statut: "" });

function statutDe(e) {
  if (e.raison === "autorisation_manuelle") return "manuel";
  return e.resultat === "granted" ? "autorise" : "refuse";
}

export default function Journal() {
  const [acces, setAcces] = useState([]);
  const [salles, setSalles] = useState([]);
  const [users, setUsers] = useState([]);
  const [f, setF] = useState(initial);
  const [erreur, setErreur] = useState("");
  const [cible, setCible] = useState(null);

  const charger = useCallback(() => {
    getAcces().then((d) => { setAcces(d); setErreur(""); }).catch((e) => setErreur(e.message));
  }, []);

  useEffect(() => {
    charger();
    const id = setInterval(charger, 10000);
    return () => clearInterval(id);
  }, [charger]);

  useEffect(() => {
    getSalles().then(setSalles).catch(() => {});
    getUtilisateurs().then(setUsers).catch(() => {});
  }, []);

  const events = useMemo(() => acces.map((e) => ({ ...e, d: new Date(e.heure) })), [acces]);

  // Refus qui ont déjà une autorisation manuelle
  const autorises = useMemo(
    () => new Set(events.filter((e) => e.refus_heure).map((e) => `${e.salle}|${new Date(e.refus_heure).getTime()}`)),
    [events]
  );

  // Les compteurs suivent salle, date et heure ; le tableau suit aussi le statut
  const base = events.filter(
    (e) =>
      (!f.salle || e.salle === f.salle) &&
      (!f.date || jour(e.d) === f.date) &&
      (!f.de || heure(e.d) >= f.de) &&
      (!f.a || heure(e.d) <= f.a)
  );
  const lignes = base.filter((e) => !f.statut || statutDe(e) === f.statut);

  const refus = base.filter((e) => e.resultat === "denied").length;
  const manuelles = base.filter((e) => statutDe(e) === "manuel").length;
  const entrees = base.length - refus;
  const taux = base.length ? Math.round((refus / base.length) * 100) : 0;

  const set = (k) => (ev) => setF({ ...f, [k]: ev.target.value });

  return (
    <div className="journal">
      <div className="filtres">
        <label>Salle
          <select value={f.salle} onChange={set("salle")}>
            <option value="">Toutes</option>
            {salles.map((s) => <option key={s.id} value={s.nom}>{s.nom}</option>)}
          </select>
        </label>
        <label>Date<input type="date" value={f.date} onChange={set("date")} /></label>
        <label>Heure de<input type="time" value={f.de} onChange={set("de")} /></label>
        <label>Heure à<input type="time" value={f.a} onChange={set("a")} /></label>
        <label>Statut
          <select value={f.statut} onChange={set("statut")}>
            <option value="">Tous</option>
            <option value="autorise">Autorisé</option>
            <option value="refuse">Refusé</option>
            <option value="manuel">Manuel</option>
          </select>
        </label>
        <button className="lien" onClick={() => setF({ ...initial(), date: "" })}>Réinitialiser</button>
      </div>

      {erreur && <div className="erreur">Impossible de charger le journal : {erreur}</div>}

      <div className="compteurs">
        <div className="compteur"><span>Entrées</span><b>{entrees}</b><em>dont {manuelles} manuelle{manuelles > 1 ? "s" : ""}</em></div>
        <div className="compteur"><span>Refus</span><b className="rouge">{refus}</b><em>à vérifier</em></div>
        <div className="compteur"><span>Taux de refus</span><b>{taux} %</b><em>sur {base.length} tentative{base.length > 1 ? "s" : ""}</em></div>
      </div>

      <div className="tableau">
        <table>
          <thead>
            <tr><th>Étudiant</th><th>Salle</th><th>Date</th><th>Heure d’entrée</th><th>Statut</th><th>Action</th></tr>
          </thead>
          <tbody>
            {lignes.length === 0 && (
              <tr><td colSpan={6} className="vide">Aucun accès pour ces filtres.</td></tr>
            )}
            {lignes.map((e, i) => {
              const st = statutDe(e);
              const [libelle, classe] = STATUTS[st];
              const deja = st === "refuse" && autorises.has(`${e.salle}|${e.d.getTime()}`);
              const detail =
                st === "refuse" ? RAISONS[e.raison] || e.raison
                : st === "manuel" ? `par ${e.valide_par}${e.motif ? " · " + e.motif : ""}`
                : "";
              return (
                <tr key={e.heure + e.salle + i}>
                  <td>{e.nom || `Badge inconnu (${(e.uid_hash || "").slice(0, 6)})`}</td>
                  <td>{e.salle}</td>
                  <td>{e.d.toLocaleDateString("fr-FR")}</td>
                  <td>{heure(e.d)}</td>
                  <td>
                    <span className={"badge " + classe}>{libelle}</span>
                    {detail && <div className="detail">{detail}</div>}
                  </td>
                  <td>
                    {st === "refuse" && !deja && (
                      <button className="btn-autoriser" onClick={() => setCible(e)}>Autoriser</button>
                    )}
                    {deja && <span className="detail">Déjà autorisé</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {cible && (
        <Modal
          cible={cible}
          users={users}
          onClose={() => setCible(null)}
          onDone={() => { setCible(null); charger(); }}
        />
      )}
    </div>
  );
}

function Modal({ cible, users, onClose, onDone }) {
  const etudiants = users.filter((u) => u.role === "etudiant");
  const valideurs = users.filter((u) => u.role === "enseignant" || u.role === "admin");
  const devine = users.find((u) => `${u.prenom} ${u.nom}` === cible.nom);

  const [etudiant, setEtudiant] = useState(devine ? String(devine.id) : "");
  const [valideur, setValideur] = useState("");
  const [motif, setMotif] = useState("");
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);

  const valider = async () => {
    setEnvoi(true);
    setErreur("");
    try {
      await autoriserManuellement({
        utilisateur_id: Number(etudiant),
        salle: cible.salle,
        valide_par: Number(valideur),
        motif: motif || null,
        refus_heure: cible.heure,
      });
      onDone();
    } catch (e) {
      setErreur(e.message);
      setEnvoi(false);
    }
  };

  return (
    <div className="voile" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <h2>Autoriser l’accès</h2>
        <p className="detail">{cible.nom || "Badge inconnu"} · {cible.salle} · {heure(cible.d)}</p>
        <label>Étudiant
          <select value={etudiant} onChange={(e) => setEtudiant(e.target.value)}>
            <option value="">Choisir…</option>
            {etudiants.map((u) => <option key={u.id} value={u.id}>{u.prenom} {u.nom}</option>)}
          </select>
        </label>
        <label>Validé par
          <select value={valideur} onChange={(e) => setValideur(e.target.value)}>
            <option value="">Choisir…</option>
            {valideurs.map((u) => <option key={u.id} value={u.id}>{u.prenom} {u.nom}</option>)}
          </select>
        </label>
        <label>Motif (facultatif)
          <input value={motif} onChange={(e) => setMotif(e.target.value)} placeholder="Badge oublié" />
        </label>
        {erreur && <div className="erreur">{erreur}</div>}
        <div className="modal__actions">
          <button className="lien" onClick={onClose}>Annuler</button>
          <button className="btn-primaire" disabled={!etudiant || !valideur || envoi} onClick={valider}>
            Autoriser l’accès
          </button>
        </div>
      </div>
    </div>
  );
}
