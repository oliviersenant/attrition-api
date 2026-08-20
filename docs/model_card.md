# Model Card — Prédiction d'attrition des employés (Futurisys)

Document technique du modèle exposé par l'API. Il décrit ce que le modèle fait, ses performances,
ses limites, et le protocole de maintenance. Complète la doc d'API (Swagger `/docs`), le schéma de
base ([db_schema.md](db_schema.md)) et le guide de déploiement ([deploiement.md](deploiement.md)).

## 1. Description

| | |
|---|---|
| **Tâche** | Classification binaire supervisée — un employé va-t-il quitter l'entreprise ? |
| **Cible** | `a_quitte_l_entreprise` (1 = a quitté, 0 = est resté) |
| **Algorithme** | `RandomForestClassifier` (scikit-learn), fine-tuné, `class_weight='balanced'` |
| **Artefact** | `Pipeline` sklearn complet `données brutes → probabilité` (sérialisé `.joblib`) |
| **Version** | 0.1.0 · scikit-learn 1.9.0 |
| **Origine** | modèle issu de la mission d'analyse d'attrition (TechNova), industrialisé ici |

**Hyperparamètres** : `n_estimators=300, max_depth=8, min_samples_leaf=10, min_samples_split=5,
max_features='log2', class_weight='balanced', random_state=42` (issus d'un `RandomizedSearchCV`
piloté par le F-beta β=2).

## 2. Données

- **Sources** : 3 extraits jointe en `inner` sur `id_employee` — SIRH, évaluations, sondage.
- **Volume** : 1470 employés, dont **237 partants (~16 %)** → déséquilibre ~1:5.
- **Entrées du modèle** : 25 champs bruts par employé (démographie, rémunération, ancienneté,
  satisfaction, heures supplémentaires, formation…) + **4 features métier créées**
  (`satisfaction_moyenne`, `ratio_stagnation_promo`, `ratio_anciennete_poste`,
  `revenu_par_annee_exp`). Les 7 variables catégorielles sont one-hot encodées
  (`OneHotEncoder(handle_unknown='ignore')`).
- **Colonnes écartées** (aucune information, cf. analyse) : constantes, quasi-constante, redondante
  (`niveau_hierarchique_poste` ~ `revenu_mensuel`), identifiant.
- **Aucune valeur manquante** (jointure interne).

## 3. Performances

Mesurées sur un **jeu de test (25 %) jamais vu**, au seuil de décision optimal :

| Métrique (classe « part ») | Valeur |
|---|---|
| Rappel | **0.71** (≈ 7 partants détectés sur 10) |
| Précision | 0.34 |
| F-beta (β=2) | 0.58 |
| PR-AUC | 0.43 |

**Métrique de pilotage : le rappel** (via F-beta β=2), pas l'accuracy. *Pourquoi :* avec un
déséquilibre 1:5, prédire « personne ne part » donne 84 % d'accuracy et **zéro utilité** ; le coût
métier d'un départ raté (faux négatif) dépasse celui d'une fausse alerte (faux positif).

### Seuil de décision — une politique métier, pas 0.5

La décision se prend à **`proba ≥ 0.415`** (et non 0.5). Ce seuil est choisi **sur le train
uniquement**, par prédictions out-of-fold puis maximisation du F-beta β=2 (aucune fuite du test). Il
vit **côté service** (dans `metadata.json`, appliqué par l'API), pas dans le modèle : on peut
l'ajuster selon la capacité de rétention réelle des RH **sans réentraîner**. Abaisser le seuil →
plus de rappel, moins de précision (plus de fausses alertes) ; l'élever → l'inverse.

## 4. Usage prévu — et limites

**Usage prévu** : un **outil d'alerte** à destination des RH, qui signale les employés à risque pour
déclencher un entretien / une action de rétention. **Ce n'est pas un oracle** ni une décision
automatique.

**Limites & précautions :**
- **Petit dataset** (1470 lignes, 237 partants) : les estimations sont bruitées ; performances à
  confirmer sur données réelles à plus grande échelle.
- **Extrapolation** : l'API accepte des valeurs hors des bornes d'entraînement (ex. âge > 60) ; les
  prédictions y sont moins fiables.
- **Précision modérée (0.34)** : ~2 alertes sur 3 sont des fausses alertes — acceptable pour un
  outil d'alerte (on préfère ratisser large), à condition que l'humain tranche.
- **Corrélations ≠ causes** : le modèle capte des associations (ex. heures supplémentaires ↔ départ),
  pas des relations causales. Il oriente l'attention, il ne prescrit pas.

**Considérations éthiques :** le modèle porte sur des **personnes**. Il ne doit jamais fonder seul
une décision défavorable (non-promotion, licenciement). Garder **l'humain dans la boucle**,
documenter les décisions, et pouvoir **expliquer** un score (l'analyse SHAP de la mission amont
fournit l'importance globale et locale des facteurs). Attention aux variables sensibles (genre,
statut marital) : à surveiller pour éviter des décisions discriminantes.

## 5. Traçabilité & monitoring

Chaque prédiction est **enregistrée en base** (table `predictions` : input reçu + output + seuil +
version + horodatage). Cette trace permet :
- l'**audit** d'une alerte a posteriori ;
- le **suivi de dérive** : comparer la distribution des inputs de production à celle du train
  (si le profil des données reçues s'éloigne, le modèle travaille hors de son domaine
  d'apprentissage) ;
- la constitution d'un **jeu de réentraînement** à partir de cas réels.

## 6. Protocole de mise à jour

**Quand réentraîner :**
- dérive détectée (les inputs de prod divergent du train, ou le rappel réel chute) ;
- arrivée de **nouvelles données** étiquetées (départs réels observés) ;
- révision périodique (ex. trimestrielle).

**Comment (reproductible et automatisé) :**
1. mettre à jour les données / le code d'entraînement ;
2. `python -m ml.train` régénère l'artefact **et recalcule le seuil** (déterministe, graine fixe) ;
3. valider les métriques (garde-fou : rappel ≥ niveau de référence — vérifié par les tests) ;
4. `git tag vX.Y.Z && git push` → la **CI/CD** rejoue les tests puis **redéploie** (le modèle est
   ré-entraîné au build). Aucun binaire n'est transporté : l'artefact est toujours reconstruit à
   partir du code + des données versionnés.

**Réglage sans réentraînement :** ajuster le **seuil** dans `metadata.json` suffit à déplacer le
curseur précision/rappel selon le besoin métier du moment.

## 7. Maintenance technique

- **Dépendances** verrouillées (`uv.lock`) ; CI sur `uv sync --locked` → environnement reproductible.
- **Tests** : 50+ tests (unitaires + fonctionnels), couverture ≥ 90 % imposée en CI.
- **Sécurité** : endpoints de prédiction protégés par clé d'API ; secrets hors du dépôt.
