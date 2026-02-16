# Aide EtaComp

> Version : 2K25 — Module de vérification des comparateurs à tige rentrante

---

## 1) Aperçu

EtaComp est une application qui permet de conduire pas à pas la vérification métrologique des **comparateurs mécaniques à cadran** ou des **comparateurs numériques à tige rentrante**. Pour cela, elle utilise deux éléments matériels :

* un **banc de contrôle** (par exemple le modèle BZMA-4Q044501E),
* un **dispositif TESA** qui joue le rôle d’étalon de référence et qui transmet les mesures au logiciel.

EtaComp offre les fonctions suivantes :

* définition d’un profil de comparateur avec ses caractéristiques principales et les points de mesure,
* conduite d’une campagne de mesures dans le sens de montée puis dans le sens de descente, selon plusieurs séries,
* calcul des différentes erreurs (erreur totale, erreur locale, erreur de fidélité, erreur d’hystérésis),
* génération d’un rapport de vérification et export des résultats.

> **Conditions préalables** : la vérification doit être réalisée dans un laboratoire stabilisé en température (20 °C ± 2 °C). L’opérateur doit également préparer l’instrument en le nettoyant, en vérifiant qu’il n’existe pas de point dur, et en s’assurant que la touche de contact est en bon état.

---

## 2) Dépendances matérielles (dispositif TESA)

EtaComp fonctionne en liaison avec un **dispositif TESA** qui peut être une colonne de mesure ou un afficheur numérique. Ce dispositif est relié au PC pour fournir les mesures de référence.

### 2.1 Interfaces supportées

* Connexion possible par câble USB (émulation de port série) ou par interface RS‑232 avec adaptateur.
* Les paramètres de communication sont configurables : port COM, vitesse de transmission, bits de données, parité, bits d’arrêt, caractère de fin de trame.
* Le protocole utilisé est simple : des trames de texte ASCII contenant la valeur mesurée et l’unité (en millimètres).

### 2.2 Prérequis

* Le pilote du câble ou de l’interface doit être installé et le port série doit être visible par le système d’exploitation.
* La longueur de course définie sur le dispositif TESA et le point zéro doivent correspondre au zéro mécanique fixé sur le banc de contrôle.

### 2.3 Test de la liaison

1. Brancher le dispositif TESA et sélectionner le port COM dans EtaComp.
2. Cliquer sur le bouton **Tester la connexion** : la dernière valeur mesurée doit s’afficher en direct.
3. Cliquer sur le bouton **Fixer zéro** pour aligner la référence du logiciel sur le zéro du dispositif TESA.

---

## 3) Flux de travail

### 3.1 Bibliothèque de comparateurs

L’utilisateur peut créer ou modifier un comparateur en renseignant :

* la référence, le fabricant et une description,
* la valeur d’échelon (appelée aussi résolution ou graduation), exprimée en millimètres (par exemple 0,01 mm ou 0,001 mm),
* la course nominale, exprimée en millimètres (par exemple 10 mm ou 30 mm),
* la famille de course (normale, grande, faible ou limitée),
* les onze points de mesure répartis uniformément dans la course, y compris le zéro.

Le profil est sauvegardé au format JSON dans le répertoire `comparators/`.

**Exemple de fichier JSON** :

```json
{
  "reference": "Mitutoyo1",
  "manufacturer": "Mitutoyo",
  "description": "Comparateur de course 10 mm avec graduation 0,01 mm",
  "graduation": 0.01,
  "course": 10.0,
  "range_type": "normale",
  "targets": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
}
```

**Exemple de fichier JSON** :

```json
{
  "reference": "Mitutoyo1",
  "manufacturer": "Mitutoyo",
  "description": "Comparateur de course 10 mm avec graduation 0,01 mm",
  "graduation": 0.01,
  "course": 10.0,
  "range_type": "normale",
  "targets": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
}
```

### 3.2 Session de vérification

1. Sélectionner un comparateur existant dans la bibliothèque.
2. Renseigner les conditions de contrôle : opérateur, date et heure, température et humidité du laboratoire, observations éventuelles.
3. Aligner le comparateur sur le zéro mécanique du banc.
4. Vérifier la connexion et le zéro du dispositif TESA dans l’onglet Matériel.
5. Lancer la campagne de mesures.

### 3.3 Déroulement des séries de mesures

EtaComp guide l’opérateur étape par étape :

* Série 1 : mesures dans le sens de la montée sur les onze points cibles,
* Série 2 : mesures dans le sens de la descente sur les onze points cibles,
* Série 3 : répétition de la série de montée,
* Série 4 : répétition de la série de descente.

> Conseil : à la fin d’une série, dépasser légèrement le dernier point de mesure avant d’inverser le sens pour la série suivante.

Ensuite, EtaComp identifie le point et le sens où l’erreur totale est la plus grande. Le logiciel demande alors :

* Série 5 : cinq mesures successives sur ce point et dans ce sens, avec retour mécanique complet entre chaque relevé. Cette série sert au calcul de l’erreur de fidélité.

### 3.4 Saisie et enregistrement

* Les valeurs provenant du dispositif TESA sont lues automatiquement lorsque la cible est atteinte, ou manuellement si l’opérateur clique sur le bouton *Prendre mesure*.
* Toutes les acquisitions sont enregistrées avec un horodatage, la cible, le sens, la valeur mesurée et l’écart.
* Le tableau de résultats superpose les lignes de montée et de descente et calcule les moyennes pour chaque point.

---

## 4) Calculs et critères

### 4.1 Définitions

* **Erreur de mesure** : différence entre la valeur mesurée et la valeur de référence.
* **Erreur totale** : plus grande des erreurs de mesure sur l’ensemble de la course.
* **Erreur locale** : plus grande différence entre deux erreurs de mesure sur deux points successifs.
* **Erreur de fidélité** : écart-type des cinq mesures effectuées au point critique dans le même sens.
* **Erreur d’hystérésis** : différence absolue entre la mesure en montée et la mesure en descente pour un même point.

### 4.2 Résultats produits

* Courbe d’étalonnage dans les deux sens,
* Tableau récapitulatif des écarts et des statistiques,
* Rapport de vérification exportable en PDF ou Excel, indiquant l’aptitude ou non du comparateur selon les tolérances configurées.

---

## 5) Conditions générales du contrôle

### 5.1 Principe

Un comparateur est déclaré **apte** si toutes les erreurs calculées (totale, locale, fidélité, hystérésis) sont inférieures aux valeurs maximales tolérées fixées pour sa famille (comparateur à course normale, grande course, faible course, ou course limitée). Si au moins une valeur dépasse la tolérance, l’instrument est considéré comme **inapte**.

### 5.2 Tolérances maximales admissibles

Les limites dépendent de la **valeur d’échelon** (graduation) et, selon la famille, éventuellement de **plages de course**.

* Pour les **comparateurs à course normale** et **à grande course**, les tolérances varient selon la **graduation (valeur unique)** et des **plages de course** exprimées en millimètres.
* Pour les **comparateurs à faible course** et **à course limitée**, **il n’y a pas de limites de course** à définir : les tolérances dépendent **uniquement** de la **graduation (valeur unique)**.

EtaComp utilise un fichier `rules/tolerances.json` pour stocker ces règles. Le format ci‑dessous remplace l’ancienne version (qui utilisait des *min/max* de graduation).

```json
{
  "normale": [
    { "graduation": 0.01,  "course_min": 5.0,  "course_max": 10.0,  "Emt": null, "Eml": null, "Ef": null, "Eh": null },
    { "graduation": 0.01,  "course_min": 10.0, "course_max": 20.0,  "Emt": null, "Eml": null, "Ef": null, "Eh": null }
  ],
  "grande": [
    { "graduation": 0.01,  "course_min": 20.0, "course_max": 30.0,  "Emt": null, "Eml": null, "Ef": null, "Eh": null }
  ],
  "faible": [
    { "graduation": 0.001, "Emt": null, "Eml": null, "Ef": null, "Eh": null }
  ],
  "limitee": [
    { "graduation": 0.001, "Emt": null, "Eml": null, "Ef": null, "Eh": null }
  ]
}
```

> Remarque \:Les **valeurs exactes** des limites (Emt, Eml, Ef, Eh) doivent être reproduites depuis vos référentiels officiels. Les exemples ci‑dessus montrent uniquement la **structure** attendue.

---

## 6) Exports

EtaComp permet d’exporter :

* les mesures brutes au format CSV,
* les résultats au format Excel avec plusieurs feuilles (mesures, courbes, synthèse),
* un constat de vérification signé au format PDF qui inclut l’identité, les conditions, les résultats et la conclusion.

---

## 7) Interface (onglets)

* **Session** : saisie des conditions, sélection du comparateur, lancement des séries, commandes liées au dispositif TESA.
* **Mesures** : tableau des résultats avec les séries de montée et de descente superposées et les moyennes, graphiques des écarts.
* **Écarts de fidélité** *(nouvel onglet)* : analyse détaillée de la série de cinq mesures au point critique.
* **Courbe d’étalonnage** *(nouvel onglet)* : visualisation de la courbe montée / descente et des écarts associés.
* **Finalisation** *(nouvel onglet)* : contrôle de complétude, application des tolérances et génération du constat.
* **Bibliothèque des comparateurs** : création, modification et suppression des profils ; chaque ligne regroupe les champs principaux et les valeurs de déroulé si présentes.
* **Paramètres** : configuration du matériel TESA, définition des tolérances, choix des thèmes d’interface, chemins d’export.

### 7.1 Écarts de fidélité (analyse des cinq mesures)

Cet onglet présentera, pour le point et le sens où l’erreur totale est maximale :

* la **liste des cinq relevés** (valeurs individuelles et temps d’acquisition),
* la **moyenne** et l’**écart-type** calculés selon la définition de l’erreur de fidélité,
* des **indicateurs visuels** (barres ou jauges) pour situer la fidélité par rapport à la tolérance,
* un **graphique** simple (série temporelle ou histogramme) pour apprécier la dispersion,
* des **messages d’aide** à l’interprétation (par exemple « dispersion élevée, vérifier la répétabilité »),
* un **lien** pour revenir à la série concernée dans l’onglet Mesures si une reprise est nécessaire.

> Statut : fonctionnalités à implémenter. L’onglet affichera des données dès que la série de fidélité aura été réalisée.

### 7.2 Courbe d’étalonnage (visualisation)

Cet onglet proposera :

* la **courbe montée** et la **courbe descente** tracées l’une sur l’autre,
* le **nuage des écarts** (mesure moins référence) en fonction des points cibles,
* l’affichage de l’**hystérésis** point par point (différence montée vs descente),
* des **curseurs** ou un **survol** pour lire précisément les valeurs,
* des **options d’export** (image et données) pour intégration au rapport,
* des **seuils visuels** correspondant aux tolérances actives pour une lecture immédiate.

> Statut : à compléter. Les graphiques se mettront à jour automatiquement lorsque de nouvelles mesures seront ajoutées.

### 7.3 Finalisation (contrôle et génération du rapport)

Cet onglet guidera l’opérateur jusqu’à la conclusion :

* **contrôle de complétude** (toutes les séries effectuées, valeurs présentes, dates et signatures),
* **application des tolérances** en fonction de la famille, de la course et de la valeur d’échelon (règles chargées depuis `rules/tolerances.json`),
* **diagnostic global** (apte ou inapte) avec explication des dépassements éventuels,
* **champ d’observations** et **synthèse** destinée au constat,
* **génération** du rapport (PDF/Excel), sauvegarde des fichiers et **archivage** du projet,
* rappel des **bonnes pratiques** (apposer l’étiquette, consigner la décision, notifier le demandeur si nécessaire).

> Statut : en cours de définition. L’onglet restera accessible en lecture après la génération pour permettre une réémission des documents si besoin.

### 7.4 Paramètres ▸ Règles (pourquoi et comment)

Cet onglet sert à **définir les tolérances** qui permettront au logiciel de conclure si un comparateur est **apte** ou **inapte** à l’issue des mesures. Les règles sont utilisées dans les onglets **Mesures**, **Écarts de fidélité**, **Courbe d’étalonnage** (pour afficher des seuils) et **Finalisation** (pour le verdict et la justification).

#### 7.4.1 Ce que couvre une « règle »

Une règle précise, pour une **famille de comparateurs**, les **caractéristiques instrumentales** et les **limites** associées :

* **Famille** : *course normale*, *grande course*, *faible course*, *course limitée*.
* **Graduation** : **valeur unique** de la résolution (en millimètres). Exemple : `0.010` mm ou `0.001` mm.
* **Plage de course** (en millimètres) : **uniquement pour les familles “course normale” et “grande course”**. Exemple : de 5 mm à 20 mm. Pour les familles **“faible course”** et **“course limitée”**, **aucune plage de course** n’est définie.
* **Limites** (en millimètres) : erreur totale, erreur locale, erreur de fidélité, erreur d’hystérésis.

Le logiciel **choisit automatiquement** la règle applicable à partir du profil du comparateur : famille, **graduation exacte**, et, si nécessaire, **course comprise dans une plage** (pour “normale” et “grande”). S’il n’existe **aucune** règle couvrant ce profil, l’état devient **indéterminé** et un message explique comment compléter la configuration.

#### 7.4.2 Comprendre les familles de course

* **Course normale** : comparateurs usuels dont la course est **intermédiaire** (par exemple autour de 10 mm). C’est le cas le plus répandu.
* **Course longue** : comparateurs permettant des **déplacements plus importants** (par exemple autour de 20 à 30 mm et au‑delà). Ils sont utiles pour des contrôles nécessitant une grande amplitude.
* **Faible course** : comparateurs destinés à des **déplacements très faibles** (par exemple environ 1 mm). Ils permettent des résolutions très fines, souvent associées à des graduations **très petites** (jusqu’à 0,001 mm).
* **Course limitée** : comparateurs dont la course est **inférieure au millimètre** (par exemple 0,5 mm). On les utilise lorsque l’on cherche avant tout la **sensibilité**, avec une plage très réduite.

> Ces définitions servent à **catégoriser** les instruments. Les **valeurs exactes** (plages et limites) doivent être renseignées selon vos référentiels internes et les normes applicables.

#### 7.4.3 Unités et cohérence

* Toutes les grandeurs sont **exprimées en millimètres** dans EtaComp. Par exemple, 13 micromètres correspondent à **0,013 mm**.
* Les limites doivent être **strictement positives**.
* Les plages doivent être **cohérentes** : la borne minimale est inférieure ou égale à la borne maximale.

#### 7.4.4 Règles qui se chevauchent

Dans une même famille, deux règles ne doivent **pas** couvrir la **même combinaison** de graduation et de course. Si un chevauchement est détecté, l’onglet affiche un **avertissement** et interdit l’enregistrement tant que la configuration n’est pas corrigée.

#### 7.4.5 Bonnes pratiques pour saisir les règles

* **Lister d’abord** vos instruments : familles, graduations courantes, courses usuelles.
* **Découper** les plages de manière lisible (par exemple 0–10 mm, 10–20 mm) et **éviter les trous**.
* **Commencer simple**, avec une règle par plage, puis affiner si nécessaire.
* **Documenter** en note interne la source des valeurs (norme, procédure, retour d’expérience).

#### 7.4.6 Exemple visuel (simplifié)

```
Famille = Course normale
Graduation 0,005 à 0,010 mm ; Course 5 à 20 mm
Limites : Emt = 0,013 mm ; Eml = 0,010 mm ; Ef = 0,003 mm ; Eh = 0,010 mm
```

#### 7.4.7 Où sont stockées les règles

Les règles sont enregistrées dans le fichier `rules/tolerances.json`. Vous pouvez les **exporter**, **importer** ou **restaurer** des valeurs par défaut à partir de cet onglet. Un **contrôle de validité** prévient les erreurs les plus fréquentes.

---

## 8) Dépannage (dispositif TESA)

* Si le port est indisponible : vérifier le pilote, le câble, les droits d’accès et le numéro de port COM.
* Si les valeurs sont instables : attendre la stabilisation, vérifier la touche de contact, la pression exercée, l’absence de jeu mécanique.
* Si le zéro est incohérent : réaligner le zéro TESA avec le zéro mécanique du banc.
* Si les trames sont invalides : vérifier les paramètres de communication série (vitesse, parité, terminaison).

---

## 9) Bonnes pratiques

* Laisser stabiliser le comparateur et le banc dans le laboratoire avant les mesures.
* Nettoyer la touche et vérifier l’absence de points durs.
* Dépasser légèrement la dernière cible avant d’inverser le sens.
* Respecter le retour mécanique complet entre chaque mesure de la série de fidélité.

---

## 10) Traçabilité et fichiers

* Chaque projet de vérification est enregistré dans un dossier horodaté.
* Les fichiers de travail incluent `session.json`, `measures.json` et `results.json`.
* Le rapport comporte les signatures de l’opérateur, du vérificateur et de l’approbateur.

---

## 11) Mentions

* Le banc de contrôle doit être compatible avec EtaComp.
* Un dispositif TESA est requis pour l’acquisition et l’étalonnage.

---

### Annexes

* Glossaire : montée, descente, erreur totale, erreur locale, fidélité, hystérésis, cible, étendue.
* Modèle de constat : voir le fichier *Constat\_Vérification\_EtaComp.xlsx* fourni avec l’application.
