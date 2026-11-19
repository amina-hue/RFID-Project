import { useCallback, useEffect, useMemo, useState } from "react";
import { getAcces, getSalles, getUtilisateurs, autoriserManuellement } from "../api";
import { creerDemo } from "./donnees-demo";
import "./journal-prof.css";

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
// Valeurs par défaut de la maquette : aujourd'hui, de 08:00 à 18:00
const initial = () => ({ salle: "", date: jour(new Date()), de: "08:00", a: "18:00", statut: "" });

// true = toujours afficher les données de démonstration, même si l'API répond
const FORCER_DEMO = false;

function statutDe(e) {
  if (e.raison === "autorisation_manuelle") return "manuel";
  return e.resultat === "granted" ? "autorise" : "refuse";
}

// Heure de sortie : champ optionnel "heure_sortie" renvoyé par l'API (absent = pas encore sorti)
function heureSortie(e) {
  return e.heure_sortie ? heure(new Date(e.heure_sortie)) : "—";
}

function useHorloge() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now.toLocaleTimeString("fr-FR");
}

export default function JournalProf() {
  const horloge = useHorloge();
  const [acces, setAcces] = useState([]);
  const [salles, setSalles] = useState([]);
  const [users, setUsers] = useState([]);
  const [f, setF] = useState(initial);             // valeurs en cours de saisie
  const [filtres, setFiltres] = useState(initial); // filtres appliqués (bouton Filtrer)
  const [erreur, setErreur] = useState("");
  const [cible, setCible] = useState(null);
  const [demo, setDemo] = useState(creerDemo);

  // Sans API (ou FORCER_DEMO), on affiche les étudiants statiques de la maquette
  const modeDemo = FORCER_DEMO || erreur !== "";
  const source = modeDemo ? demo : acces;
  const listeSalles = modeDemo
    ? [...new Set(demo.map((e) => e.salle))].map((nom, id) => ({ id, nom }))
    : salles;
  const nbSalles = modeDemo ? 3 : salles.length;

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

  // d = heure de l'événement ; entree = heure d'entrée affichée.
  // Pour une autorisation manuelle, l'entrée est l'heure du refus d'origine (d = heure de validation).
  const events = useMemo(
    () =>
      source.map((e) => {
        const d = new Date(e.heure);
        const manuel = e.raison === "autorisation_manuelle";
        return { ...e, d, entree: manuel && e.refus_heure ? new Date(e.refus_heure) : d };
      }),
    [source]
  );

  // Les refus déjà autorisés à la main sont remplacés par la ligne « Manuel »
  const visibles = useMemo(() => {
    const autorises = new Set(
      events.filter((e) => e.refus_heure).map((e) => `${e.salle}|${new Date(e.refus_heure).getTime()}`)
    );
    return events.filter((e) => !(e.resultat === "denied" && autorises.has(`${e.salle}|${e.d.getTime()}`)));
  }, [events]);

  // Personnes présentes : entrées acceptées aujourd'hui, sans heure de sortie, une fois par personne
  const presents = useMemo(() => {
    const aujourdhui = jour(new Date());
    const personnes = new Set();
    events.forEach((e) => {
      if (e.resultat !== "granted" || e.heure_sortie) return;
      if (jour(e.entree) !== aujourdhui) return;
      personnes.add(e.nom || e.uid_hash);
    });
    return personnes.size;
  }, [events]);

  const lignes = visibles
    .filter(
      (e) =>
        (!filtres.salle || e.salle === filtres.salle) &&
        (!filtres.date || jour(e.entree) === filtres.date) &&
        (!filtres.de || heure(e.entree) >= filtres.de) &&
        (!filtres.a || heure(e.entree) <= filtres.a) &&
        (!filtres.statut || statutDe(e) === filtres.statut)
    )
    .sort((a, b) => a.entree - b.entree);

  // En démonstration : « Autoriser » ajoute une ligne Manuel locale, sans appeler l'API
  const autoriserDemo = (e) =>
    setDemo((d) => [
      ...d,
      {
        heure: new Date().toISOString(), salle: e.salle, nom: e.nom, uid_hash: e.uid_hash,
        resultat: "granted", raison: "autorisation_manuelle", valide_par: "Pr. Karim Haddad",
        motif: null, refus_heure: e.heure,
      },
    ]);

  const set = (k) => (ev) => setF({ ...f, [k]: ev.target.value });

  const appliquer = (ev) => {
    ev.preventDefault();
    setFiltres(f);
  };

  const reinitialiser = () => {
    const i = initial();
    setF(i);
    setFiltres(i);
  };

  return (
    <div className="jp">
      <div className="jp-contenu">
        <header className="jp-entete">
          <div>
            <h1>Journal</h1>
            <p>Historique des accès à mes salles</p>
          </div>
          <div className="jp-entete__droite">
            <span className="jp-lecture">Lecture seule</span>
            <div className="jp-horloge">{horloge}</div>
            {/* Bouton décoratif pour l'instant : aucune action branchée */}
            <button type="button" className="jp-salles">Mes salles</button>
          </div>
        </header>

        <div className="jp-presence">
          <div className="jp-presence__icone" aria-hidden="true" />
          <div>
            <span>Personnes présentes</span>
            <div className="jp-presence__valeur">
              <b>{modeDemo ? 37 : presents}</b>
              <em>sur {nbSalles} salle{nbSalles > 1 ? "s" : ""}</em>
            </div>
          </div>
        </div>

        <hr className="jp-separateur" />

        <div className="jp-section">
          <h2>Accès des étudiants</h2>
          <p>Étudiants ayant accédé à leur séance, tentatives refusées incluses</p>
        </div>

        <form className="jp-filtres" onSubmit={appliquer}>
          <label>Salle
            <select value={f.salle} onChange={set("salle")}>
              <option value="">Toutes</option>
              {listeSalles.map((s) => <option key={s.id} value={s.nom}>{s.nom}</option>)}
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
          <button type="submit" className="jp-btn jp-btn--plein jp-btn--filtrer">Filtrer</button>
          <button type="button" className="jp-lien" onClick={reinitialiser}>Réinitialiser</button>
        </form>

        {modeDemo && (
          <div className="jp-demo">
            Données de démonstration{erreur ? ` (API injoignable : ${erreur})` : ""}
          </div>
        )}

        <div className="jp-tableau">
          <table>
            <thead>
              <tr>
                <th>Étudiant</th><th>Salle</th><th>Date</th><th>Heure d’entrée</th>
                <th>Heure de sortie</th><th>Statut</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {lignes.length === 0 && (
                <tr><td colSpan={7} className="jp-vide">Aucun accès pour ces filtres.</td></tr>
              )}
              {lignes.map((e, i) => {
                const st = statutDe(e);
                const [libelle, classe] = STATUTS[st];
                const detail =
                  st === "refuse" ? RAISONS[e.raison] || e.raison
                  : st === "manuel" ? `par ${e.valide_par} · ${heure(e.d)}`
                  : "";
                return (
                  <tr key={e.heure + e.salle + i}>
                    <td>{e.nom || `Badge inconnu (${(e.uid_hash || "").slice(0, 6)})`}</td>
                    <td>{e.salle}</td>
                    <td>{e.entree.toLocaleDateString("fr-FR")}</td>
                    <td>{heure(e.entree)}</td>
                    <td>{heureSortie(e)}</td>
                    <td>
                      <span className={"jp-badge jp-badge--" + classe}>{libelle}</span>
                      {detail && <div className="jp-detail" title={e.motif || undefined}>{detail}</div>}
                    </td>
                    <td>
                      {st === "refuse" && (
                        <button type="button" className="jp-btn jp-btn--contour" onClick={() => (modeDemo ? autoriserDemo(e) : setCible(e))}>
                          Autoriser
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {cible && (
        <Fenetre
          cible={cible}
          users={users}
          onClose={() => setCible(null)}
          onDone={() => { setCible(null); charger(); }}
        />
      )}
    </div>
  );
}

function Fenetre({ cible, users, onClose, onDone }) {
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
    <div className="jp-voile" onClick={onClose}>
      <div className="jp-fenetre" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <h2>Autoriser l’accès</h2>
        <p className="jp-detail">{cible.nom || "Badge inconnu"} · {cible.salle} · {heure(cible.entree)}</p>
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
        {erreur && <div className="jp-erreur">{erreur}</div>}
        <div className="jp-fenetre__actions">
          <button type="button" className="jp-lien" onClick={onClose}>Annuler</button>
          <button type="button" className="jp-btn jp-btn--plein" disabled={!etudiant || !valideur || envoi} onClick={valider}>
            Autoriser l’accès
          </button>
        </div>
      </div>
    </div>
  );
}