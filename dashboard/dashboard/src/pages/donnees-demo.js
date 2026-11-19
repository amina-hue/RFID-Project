// Données statiques de démonstration (celles de la maquette), utilisées quand l'API est injoignable.
// Les dates sont calculées à partir d'aujourd'hui pour qu'elles passent le filtre par défaut.
const aujourdhui = (h, m) => {
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return d.toISOString();
};

export function creerDemo() {
  return [
    {
      heure: aujourdhui(8, 2), salle: "TP1", nom: "Amine Benali", uid_hash: "a1b2c3",
      resultat: "granted", raison: "ok", heure_sortie: aujourdhui(10, 0),
    },
    {
      heure: aujourdhui(8, 5), salle: "TP1", nom: "Lina Merabet", uid_hash: "d4e5f6",
      resultat: "granted", raison: "ok", heure_sortie: aujourdhui(10, 1),
    },
    {
      heure: aujourdhui(10, 10), salle: "TP2", nom: "Yacine Haddad", uid_hash: "0a9b8c",
      resultat: "denied", raison: "salle_non_autorisee",
    },
    // Refus d'origine de Sara : remplacé à l'affichage par la ligne « Manuel » ci-dessous
    {
      heure: aujourdhui(10, 12), salle: "TP2", nom: "Sara Khelifi", uid_hash: "7d6e5f",
      resultat: "denied", raison: "badge_inconnu",
    },
    {
      heure: aujourdhui(10, 14), salle: "TP2", nom: "Sara Khelifi", uid_hash: "7d6e5f",
      resultat: "granted", raison: "autorisation_manuelle", valide_par: "Pr. Moussa",
      motif: "Badge oublié", refus_heure: aujourdhui(10, 12), heure_sortie: aujourdhui(11, 58),
    },
    {
      heure: aujourdhui(14, 0), salle: "TP3", nom: "Karim Bouzid", uid_hash: "3c4d5e",
      resultat: "granted", raison: "ok", heure_sortie: aujourdhui(16, 3),
    },
    {
      heure: aujourdhui(14, 4), salle: "TP3", nom: "Nour Silmani", uid_hash: "9f8e7d",
      resultat: "denied", raison: "hors_periode",
    },
  ];
}