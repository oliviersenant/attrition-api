# Notes de soutenance — ce que je dis (sans lire la slide)

**Règle d'or** : la slide affiche les mots-clés ; moi je raconte le *pourquoi* et je fais les
transitions. Je regarde le jury, pas l'écran. ~15 min de présentation → ~1 min par slide, je garde
de la marge pour la démo live (slides 5 et 7).

Format des notes : ce que je **dis** à l'oral + la **transition** vers la slide suivante.

---

## Slide 1 — Titre

« Bonjour, je suis Olivier Senant. Je vous présente le déploiement en production du modèle de
prédiction d'attrition — celui que j'avais analysé dans la mission précédente pour TechNova.
Aujourd'hui, le sujet n'est plus *quel modèle*, mais *comment le rendre réellement utilisable* par
Futurisys. Et il tourne : l'API est en ligne, je vous la montrerai en direct. »

→ *Transition* : « Commençons par le problème que ça résout. »

## Slide 2 — Contexte

« Le point de départ, c'est un constat simple : un modèle qui vit dans un notebook n'a aucune valeur
opérationnelle. Personne dans l'entreprise ne peut l'interroger. Ma mission, c'était de le
transformer en *service* : quelque chose qu'un logiciel RH peut appeler à tout moment, avec les
garanties d'un vrai logiciel — versionné, testé, tracé, sécurisé. Je ne refais pas de data science ;
je fais de l'ingénierie autour du modèle existant. »

→ « Voyons d'abord la vue d'ensemble, avant de rentrer dans chaque brique. »

## Slide 3 — Architecture

« Voici la chaîne complète. À gauche, je développe sur une branche. Quand je pousse, GitHub Actions
lance automatiquement les tests. Si — et seulement si — ils passent, poser une étiquette de version
déclenche le déploiement sur Render, qui reconstruit l'image et remet l'API en ligne. En bas, la
base PostgreSQL, chez Neon, qui enregistre chaque prédiction. L'idée à retenir : **du push au service
en ligne, sans que je touche à rien manuellement**. Je vais dérouler cette chaîne brique par brique. »

→ « La fondation de tout ça, c'est le dépôt Git. »

## Slide 4 — Git

« J'ai traité ce dépôt comme un projet collaboratif, pas comme un dossier de scripts. La règle : la
branche principale ne contient que du code qui marche. Chaque fonctionnalité — l'API, la base, la CI —
a été développée sur sa propre branche, puis fusionnée par Pull Request. J'ai versionné avec des tags,
de la v0.1 à la v1.0 : chaque tag est une version livrable. Résultat : un historique qui *raconte* la
mission, étape par étape. »

→ « Et ces branches ne sont pas qu'une discipline personnelle — la CI les transforme en garde-fou. »

## Slide 5 — CI/CD

« Ici, la qualité cesse d'être une bonne intention pour devenir une règle appliquée par la machine.
À chaque push, le linter et les 54 tests tournent. Tant que ce n'est pas vert, GitHub *interdit* la
fusion — le bouton est désactivé. Et pour le déploiement, j'ai fait un choix de sécurité : GitHub ne
reçoit pas les accès à Render, juste un "bouton" secret à presser. Deux fichiers YAML décrivent tout
ça : un pour les tests, un pour l'infrastructure. »

→ *(si démo)* « Je peux vous montrer un run dans l'onglet Actions. » Sinon → « Passons au cœur : le
modèle lui-même. »

## Slide 6 — Empaquetage du modèle

« C'est le point technique dont je suis le plus fier. Le bug numéro un quand on déploie un modèle,
c'est un préprocessing qui diverge entre l'entraînement et la production — et le pire, c'est qu'il est
*silencieux* : pas d'erreur, juste des prédictions fausses. Ma parade : j'emballe tout — nettoyage,
features, encodage, modèle — dans un *seul* objet. C'est le même objet qui a appris et qui prédit,
donc impossible de diverger. Détail clé : j'utilise un encodeur qui *mémorise* les catégories, ce qui
me permet de prédire même pour un seul employé, ou face à un métier jamais vu. »

→ « Cet objet, il faut maintenant l'exposer. C'est le rôle de l'API. »

## Slide 7 — API FastAPI

« L'API, c'est un guichet. On dépose les infos d'un employé, on récupère un risque de départ. Le point
important, c'est le *contrat d'entrée* : chaque champ est typé et borné. Une donnée absurde — un âge
négatif, un métier inexistant — est rejetée avec un message clair *avant* même d'atteindre le modèle.
Et la documentation Swagger est générée à partir de ce même contrat : elle ne peut donc jamais mentir.
Je vous propose de la voir en direct. »

→ *(DÉMO LIVE)* Ouvrir `/docs` → Authorize (clé) → POST /predict sur l'exemple → montrer la réponse →
GET /predictions pour montrer la trace. « Vous voyez : la prédiction, et juste en dessous, sa trace en
base. »

## Slide 8 — PostgreSQL

« Justement, cette trace. Le brief exigeait que *toute* interaction passe par la base — et c'est loin
d'être un détail administratif. Sans mémoire, une prédiction est un événement fantôme : impossible
d'auditer une alerte contestée, de détecter que les données changent, ou de réentraîner sur des cas
réels. J'ai deux tables : le dataset de référence, et l'historique des prédictions. Petit point de
conception : j'enregistre une *photo* des données reçues plutôt qu'un lien vers le dataset — parce
qu'on doit pouvoir scorer un employé qui n'y figure pas encore. »

→ « Tout ça ne vaut que si c'est fiable. D'où les tests. »

## Slide 9 — Tests & couverture

« J'ai 54 tests et 94 % de couverture, avec un plancher à 90 % : si quelqu'un fait retomber la
couverture en dessous, la CI échoue. Mais le chiffre n'est pas le sujet. Ce que je teste surtout,
c'est ce qui doit *échouer proprement* : les données invalides, la base indisponible, un modèle
absent. Ma règle personnelle : *un bug rencontré = un test écrit*. Par exemple, un piège de version de
pandas m'a coûté une heure ; il est devenu un test permanent, il ne reviendra jamais. »

→ « Et comme l'API est publique, il a fallu la protéger. »

## Slide 10 — Sécurité

« Dès qu'une API est en ligne, n'importe qui peut l'appeler. Je protège donc les endpoints par une
clé. La distinction importante : la clé *attendue* vit côté serveur, chez l'hébergeur ; le client la
*présente* à chaque appel. Aucun secret n'est dans le dépôt — ni la clé, ni le mot de passe de la
base. Le dépôt ne contient que des modèles de formulaire vides. C'est un point que le brief valorise
explicitement. »

→ « Revenons une seconde au métier : qu'est-ce que ce modèle fait, concrètement ? »

## Slide 11 — Le modèle en action

« Le modèle rend une *probabilité* de départ, et je décide avec un seuil réglé sur la priorité métier :
mieux vaut une fausse alerte qu'un départ raté. Sur ce graphe : un profil stable reste sous le seuil,
un profil junior insatisfait qui fait des heures sup ressort à 0,91 — clairement alerté. C'est un
*outil d'alerte* pour les RH, pas un oracle : l'humain reste dans la boucle, et je documente ça
noir sur blanc dans la model card. »

→ « Pour finir, je veux vous raconter un vrai incident — parce que c'est là qu'on voit la méthode. »

## Slide 12 — Incident en production

« Le jour du déploiement : tous mes tests verts, la page de santé répond… mais la prédiction renvoyait
une erreur 500. Ma démarche : d'abord *reproduire* — j'ai rejoué la logique en local contre la vraie
base de production. Ça marchait. Donc le code et la base étaient hors de cause : le problème était
dans l'environnement d'hébergement. Ensuite j'ai *lu la traceback* : il manquait un pilote de base de
données, parce que l'URL était mal formée. Je l'ai corrigé tout de suite, mais surtout j'ai corrigé la
*classe* de bug dans le code, avec des tests — pour qu'il ne puisse jamais revenir. La leçon : un code
vert en test peut échouer en prod sur une seule différence d'environnement. »

→ « Ce qui m'amène au bilan. »

## Slide 13 — Bilan

« En résumé : je suis parti d'un modèle dans un notebook, et j'arrive à un service en production —
versionné, documenté, testé, tracé, et qui se redéploie tout seul. Tous les livrables sont là. La
suite naturelle, ce serait un tableau de bord de suivi de dérive, alimenté justement par cette table
de prédictions. Je vous remercie, et je suis prêt pour vos questions. »

---

## Prêt pour la discussion (10 min) — réponses courtes

- **« Quels défis avec FastAPI ? »** → Le vrai défi n'était pas FastAPI mais l'alignement
  entraînement/production. Je l'ai réglé en emballant tout le préprocessing dans le modèle. Côté
  FastAPI, le point clé c'est la validation Pydantic : rejeter l'absurde avant le modèle.

- **« Votre stratégie de tests / couverture ? »** → Tests écrits au fil de l'eau, pas à la fin ; un
  plancher de couverture en CI ; je teste surtout les cas d'erreur ; et *un bug = un test*. Je vise un
  plancher honnête, pas 100 % cosmétique.

- **« Config de la base et intégration au modèle ? »** → URL de connexion par variable
  d'environnement (12 facteurs), ORM SQLAlchemy, un mixin pour ne pas dupliquer les colonnes, et
  chaque prédiction tracée. L'intégration se fait dans l'endpoint : prédire *puis* enregistrer, de
  façon atomique.

- **« Est-ce prêt pour la vraie production ? »** → C'est un POC fonctionnel et déployé. Pour du grand
  volume : passer le seuil de veille de Render (cold start), ajouter du monitoring de dérive, et un
  vrai système d'authentification par utilisateur plutôt qu'une clé partagée.

- **Piège à éviter à l'oral** : ne pas survendre les perfs du modèle (précision modérée, assumée) ;
  insister sur *outil d'alerte + humain dans la boucle*.
