# Spécification Fonctionnelle – Application EtaComp2K25

**Version :** 1.0  
**Date :** 18 février 2026

---

## 1. Présentation générale

### 1.1 Finalité métier

L’application EtaComp2K25 est un logiciel de **vérification métrologique des comparateurs** (capteurs de mesure de déplacement). Elle permet de :

- réaliser des campagnes de mesures sur 11 points de cible,
- calculer les erreurs de mesure (totale, locale, fidélité, hystérésis),
- évaluer la conformité du comparateur aux tolérances réglementaires,
- tracer la courbe d’étalonnage et produire une synthèse exploitable.

### 1.2 Contexte d’utilisation

- Environnement métrologique (atelier, laboratoire).
- Utilisation avec un **banc étalon** et un **dispositif de mesure** (ex. comparateur TESA) connecté en RS-232/USB.
- Les mesures peuvent être acquises automatiquement (flux série) ou saisies manuellement.

### 1.3 Type d’utilisateur cible

Opérateur métrologue : réalise les campagnes de mesure, consulte les résultats et les verdicts, exporte les documents.

### 1.4 Périmètre fonctionnel couvert

| Domaine | Couvert |
|---------|---------|
| Configuration comparateurs (11 cibles, graduation, course, famille) | Oui |
| Gestion de session (opérateur, conditions ambiantes, détenteur, banc étalon) | Oui |
| Acquisition mesures série (TESA mode bouton) | Oui |
| Campagne 4 séries (2 cycles montée/descente × 11 cibles) | Oui |
| Série 5 (fidélité au point critique) | Oui |
| Calculs d’erreurs (Emt, Eml, Ef, Eh) | Oui |
| Évaluation tolérances selon règles (famille, graduation, course) | Oui |
| Courbe d’étalonnage | Oui |
| Export PDF / HTML | Non (placeholders uniquement) |
| Sauvegarde/chargement sessions | Oui |
| Bibliothèques (comparateurs, détenteurs, bancs étalon) | Oui |

---

## 2. Architecture fonctionnelle

### 2.1 Découpage en modules

| Module | Rôle |
|--------|------|
| **models** | Objets métier : Session, MeasureSeries, FidelitySeries, Comparator, Detenteur, BancEtalon, SessionV2, Measurement, Series |
| **io/storage** | Persistance JSON : comparateurs, détenteurs, bancs étalon, sessions, export_config |
| **io/serial_manager** | Connexion série, envoi commandes, réception et parsing des trames |
| **io/tesa_reader** | Assemblage de trames TESA (silence/EOL), extraction valeur numérique |
| **state/session_store** | État global de la session courante (édition, signaux) |
| **core/session_adapter** | Conversion Session (runtime) → SessionV2 (canonique) pour les calculs |
| **core/calculation_engine** | Calcul des erreurs Emt, Eml, Eh, Ef à partir de SessionV2 |
| **rules/tolerance_engine** | Chargement règles, matching famille/graduation/course |
| **rules/verdict** | Évaluation erreurs vs limites, production verdict (apte/inapte/indéterminé) |
| **rules/tolerances** | Règles par défaut, sauvegarde/chargement pour l’UI |
| **calculations/errors** | Pont de compatibilité vers CalculationEngine |
| **ui/tabs** | Onglets Session, Mesures, Écarts fidélité, Courbe, Finalisation, Bibliothèque, Paramètres |
| **ui/results_provider** | Agrégation : SessionV2 + calculs + verdict (point d’entrée unique) |

### 2.2 Relations entre modules

```
SessionStore ←→ Session (runtime)
       ↓
session_adapter → SessionV2
       ↓
CalculationEngine → CalculatedResults
       ↓
ToleranceRuleEngine + verdict → Verdict
       ↓
ResultsProvider (agrège tout)
       ↓
UI (Finalisation, Courbe, Fidélité)
```

- **SessionStore** : source de vérité pour la session éditable.
- **session_adapter** : construit une SessionV2 à partir de Session et de la bibliothèque comparateurs.
- **CalculationEngine** : algorithme pur, sans dépendance UI.
- **ResultsProvider** : charge les règles, appelle session_adapter + engine + verdict.
- **SerialManager** : utilisé par Mesures et Fidélité pour acquérir les valeurs.

### 2.3 Diagramme logique textuel des flux

```
[Opérateur] → Session (métadonnées)
                   ↓
[Dispositif TESA] → Mesures (série) → SessionStore.set_series
                   ↓
[Onglet Fidélité] → Série 5 (5 mesures) → SessionStore.set_fidelity
                   ↓
[Finalisation] → ResultsProvider.compute_all(rt)
                   ↓
           SessionV2 ← session_adapter
                   ↓
           CalculatedResults ← CalculationEngine
                   ↓
           Verdict ← evaluate_tolerances(profile, results, engine)
                   ↓
           Affichage (apte / inapte / indéterminé)
```

---

## 3. Modèle de données

### 3.1 Objets métier

#### Session (runtime, Pydantic)

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| operator | str | Oui | Nom de l’opérateur |
| date | datetime | Non (défaut: now) | Date/heure de la session |
| temperature_c | float | Non | Température (°C) |
| humidity_pct | float | Non | Humidité (%) |
| comparator_ref | str | Non | Référence du comparateur sélectionné |
| holder_ref | str | Non | Code ES du détenteur |
| banc_ref | str | Non | Référence du banc étalon (hors défaut) |
| series_count | int | Non (défaut 0) | Nombre d’itérations (cycles) |
| measures_per_series | int | Non (défaut 0) | Mesures/série (prévu) |
| observations | str | Non | Observations texte |
| series | List[MeasureSeries] | Non | Séries par cible |
| fidelity | FidelitySeries | Non | Série 5 (fidélité) |

#### MeasureSeries

| Champ | Type | Description |
|-------|------|-------------|
| target | float | Valeur cible en mm |
| readings | List[float] | Relevés par position (voir encodage ci‑dessous) |

**Encodage readings** :  
`readings[pos]` correspond à la mesure pour  
`pos = (cycle - 1) * 2 + (0 si montée, 1 si descente)`.  
Exemple : cycle 1 montée → pos 0, cycle 1 descente → pos 1, cycle 2 montée → pos 2, etc.  
La liste peut contenir des valeurs manquantes (trous) ; les positions inutilisées ne sont pas stockées en fin de liste.

#### FidelitySeries

| Champ | Type | Description |
|-------|------|-------------|
| target | float | Cible (point critique) en mm |
| direction | str | "up" ou "down" |
| samples | List[float] | 5 valeurs en mm |
| timestamps | List[str] | Horodatages ISO (optionnel) |

#### Comparator (ComparatorProfile)

| Champ | Type | Obligatoire | Contraintes |
|-------|------|-------------|-------------|
| reference | str | Oui | min_length=1 |
| manufacturer | str | Non | |
| description | str | Non | |
| graduation | float | Oui | > 0 |
| course | float | Oui | > 0 |
| range_type | RangeType | Oui | normale, grande, faible, limitee |
| targets | List[float] | Oui | Exactement 11 valeurs |
| periodicite_controle_mois | int | Non | 1–120, défaut 12 |

**Contraintes targets** :  
- 11 cibles exactement ;  
- première cible = 0 (tolérance 1e‑6) ;  
- toutes dans [0, course] ;  
- ordre non décroissant.

#### Detenteur

| Champ | Type | Description |
|-------|------|-------------|
| code_es | str | Code identifiant |
| libelle | str | Libellé descriptif |

#### BancEtalon

| Champ | Type | Description |
|-------|------|-------------|
| reference | str | Référence unique |
| marque_capteur | str | Marque du capteur |
| date_validite | str | Date de validité (texte libre) |
| is_default | bool | Banc par défaut pour export (un seul) |

#### SessionV2 (modèle canonique pour calculs)

| Champ | Type | Description |
|-------|------|-------------|
| schema_version | int | Version du schéma |
| session_id | str | Identifiant unique |
| created_at_iso | str | Date création ISO |
| operator | str | Opérateur |
| temperature_c | float | Température |
| humidity_rh | float | Humidité |
| comparator_ref | str | Référence comparateur |
| comparator_snapshot | dict | Copie profil (graduation, course, range_type, targets) |
| notes | str | Observations |
| series | List[Series] | Séries S1–S5 avec measurements |

#### Series (SessionV2)

| Champ | Type | Description |
|-------|------|-------------|
| index | int | 1–5 |
| kind | SeriesKind | MAIN ou FIDELITY |
| direction | Direction | UP ou DOWN |
| targets_mm | List[float] | Cibles |
| measurements | List[Measurement] | Liste de Measurement |

#### Measurement (SessionV2)

| Champ | Type | Description |
|-------|------|-------------|
| target_mm | float | Cible |
| value_mm | float | Valeur mesurée |
| direction | Direction | UP/DOWN |
| series_index | int | 1–5 |
| sample_index | int | Index dans la série |
| timestamp_iso | str | Horodatage |
| display, raw_hex, raw_ascii | str | Optionnels (affichage) |

### 3.2 Structure des fichiers JSON

#### Comparateur (`comparators/{reference}.json`)

```json
{
  "reference": "TESA_Mic_001",
  "manufacturer": "TESA",
  "description": "…",
  "graduation": 0.01,
  "course": 10.0,
  "range_type": "normale",
  "targets": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "periodicite_controle_mois": 12
}
```

#### Session (`sessions/{ref}_{YYYYMMDD_HHMMSS}.json`)

Structure Pydantic Session : operator, date, temperature_c, humidity_pct, comparator_ref, holder_ref, banc_ref, series_count, measures_per_series, observations, series, fidelity.

#### Détenteurs (`detenteurs.json`)

```json
{
  "detenteurs": [
    { "code_es": "ES12345", "libelle": "Atelier principal" }
  ]
}
```

#### Bancs étalon (`bancs_etalon.json`)

```json
{
  "bancs": [
    {
      "reference": "BE-001",
      "marque_capteur": "TESA",
      "date_validite": "2025-12-31",
      "is_default": true
    }
  ]
}
```

#### Règles de tolérances (`rules/tolerances.json`)

```json
{
  "normale": [
    {
      "graduation": 0.01,
      "course_min": 0.0,
      "course_max": 5.0,
      "Emt": 0.015,
      "Eml": 0.010,
      "Ef": 0.0015,
      "Eh": 0.006
    }
  ],
  "grande": [],
  "faible": [
    { "graduation": 0.001, "Emt": 0.0015, "Ef": 0.0005, "Eh": 0.0006 }
  ],
  "limitee": []
}
```

Champs par famille :
- **normale, grande** : course_min, course_max obligatoires ; pas de chevauchement d’intervalles.
- **faible, limitee** : pas de course_min/course_max ; graduation unique par règle (pas de doublon).

#### Configuration export (`export_config.json`)

```json
{
  "entite": "14eBSMAT",
  "image_path": "/chemin/logo.png",
  "document_title": "Rapport de vérification",
  "document_reference": "EtaComp-REP-2025",
  "texte_normes": "…"
}
```

#### Configuration TESA (`tesa_config.json`)

```json
{
  "enabled": true,
  "frame_mode": "silence",
  "silence_ms": 120,
  "eol": "CRLF",
  "mask_7bit": true,
  "strip_chars": "\\r\\n\\0 ",
  "value_regex": "[-+]?\\d+(?:[.,]\\d+)?|[-+]?[.,]\\d+",
  "decimals": 3,
  "decimal_display": "dot"
}
```

### 3.3 Contraintes de cohérence

- Un seul banc étalon peut avoir `is_default: true`.
- Les sessions ne sont enregistrées que si `has_measures()` (au moins une mesure).
- Nom de fichier session : `{comparator_ref}_{YYYYMMDD_HHMMSS}.json` (espaces remplacés par `_`).
- Dossier de données : `~/.EtaComp2K25/` (sous-dossiers `comparators`, `sessions`, `rules`).

---

## 4. Gestion d’une Session

### 4.1 Cycle de vie complet

1. **Création** : bouton « Nouvelle session » → `SessionStore.new_session()`.
2. **Paramétrage** : sélection comparateur, détenteur, banc étalon, opérateur, conditions ambiantes.
3. **Acquisition** : onglet Mesures → Démarrer campagne → mesures reçues du flux série ou saisies.
4. **Fidélité (optionnel)** : après les 4 séries, capture des 5 mesures au point critique.
5. **Calcul** : onglet Finalisation → Calculer les erreurs.
6. **Sauvegarde** : enregistrement si `has_measures()`.
7. **Chargement** : chargement d’une session depuis l’historique.

### 4.2 États possibles

- **Vide** : aucune mesure.
- **Partielle** : mesures en cours (séries incomplètes).
- **Complète (sans S5)** : 4 séries remplies ; fidélité absente.
- **Complète (avec S5)** : 4 séries + série 5 ; verdict peut inclure Ef.

### 4.3 Paramètres configurables

| Paramètre | Source | Valeur par défaut |
|-----------|--------|-------------------|
| series_count | Préférences / Session | 0 (ou 2 pour 2 cycles) |
| measures_per_series | Préférences / Session | 0 |
| Nombre de cycles (Mesures) | Dérivé de series_count | 2 (S1–S4) |
| Cibles | Profil comparateur | 11 valeurs |

### 4.4 Lien avec la bibliothèque des comparateurs

- La session référence un comparateur par `comparator_ref`.
- Au calcul, un snapshot (reference, graduation, course, range_type, targets) est extrait de la bibliothèque et stocké dans `comparator_snapshot` de SessionV2.
- Les cibles de la campagne proviennent du comparateur sélectionné.

---

## 5. Calculs implémentés

### 5.1 Erreur (écart) à une cible

**Nom** : Écart (erreur) par mesure.

**Finalité** : Mesurer l’écart entre valeur mesurée et cible de référence.

**Formule** :
$$e_{i} = v_{i} - t_{i}$$

avec \(v_{i}\) = valeur mesurée (mm), \(t_{i}\) = cible (mm).

**Variables** : target_mm, value_mm pour chaque Measurement.

**Hypothèses** : Référence = cible ; pas de correction d’étalonnage du banc.

---

### 5.2 Moyenne des erreurs par cible et par sens

**Nom** : Moyenne montée / descente.

**Finalité** : Moyenne des erreurs pour un sens (montée ou descente) à une cible donnée.

**Formule** :
$$\bar{e}_{\mathrm{up}}(t) = \frac{1}{n_{\mathrm{up}}} \sum_{i \in \mathrm{up}} (v_i - t)$$
$$\bar{e}_{\mathrm{down}}(t) = \frac{1}{n_{\mathrm{down}}} \sum_{i \in \mathrm{down}} (v_i - t)$$

avec \(n\) = nombre de mesures dans ce sens pour la cible \(t\).

**Type** : Moyenne de population (pas de correction n-1).  
**ddof** : 0 (non utilisé pour la moyenne).

**Variables** : up_vals[t], down_vals[t] (listes de value_mm pour la cible t).

---

### 5.3 Erreur totale (Emt)

**Nom** : Erreur de mesure totale.

**Finalité** : Plus grande erreur (en valeur absolue) parmi toutes les cibles et les deux sens.

**Formule** :
$$\mathrm{Emt} = \max \left( \left| \bar{e}_{\mathrm{up}}(t) \right|, \left| \bar{e}_{\mathrm{down}}(t) \right| \right) \quad \forall t$$

Le résultat retourné est la valeur absolue de l’erreur maximale.

**Variables** : up_err, down_err pour chaque cible.

**Cas particuliers** : Si une seule mesure par sens, elle est prise telle quelle. Campagne partielle : calcul sur les données disponibles.

---

### 5.4 Erreur d’hystérésis (Eh)

**Nom** : Erreur d’hystérésis maximale.

**Finalité** : Plus grande différence entre moyenne montée et moyenne descente à une même cible.

**Formule** :
$$\mathrm{Eh} = \max_{t} \left| \bar{v}_{\mathrm{up}}(t) - \bar{v}_{\mathrm{down}}(t) \right|$$

avec \(\bar{v}\) = moyenne des valeurs mesurées (pas des erreurs).

**Variables** : up_m, down_m pour chaque cible.

**Cas particuliers** : Si une des deux moyennes manque pour une cible, cette cible est ignorée.

---

### 5.5 Erreur locale (Eml)

**Nom** : Erreur de mesure locale (variation entre cibles successives).

**Finalité** : Plus grande variation d’erreur entre deux cibles consécutives sur une courbe (montée ou descente).

**Formule** :
$$\mathrm{Eml}_{\mathrm{up}} = \max_{i} \left| e_{i+1} - e_i \right| \quad \text{(courbe montée)}$$
$$\mathrm{Eml}_{\mathrm{down}} = \max_{i} \left| e_{i+1} - e_i \right| \quad \text{(courbe descente)}$$
$$\mathrm{Eml} = \max(\mathrm{Eml}_{\mathrm{up}}, \mathrm{Eml}_{\mathrm{down}})$$

avec \(e_i\) = erreur à la cible \(i\) (dans l’ordre des cibles).

**Variables** : up_errors, down_errors (liste de (target, error)).

---

### 5.6 Erreur de fidélité (Ef)

**Nom** : Écart-type des 5 mesures au point critique.

**Finalité** : Dispersion des 5 mesures successives au point critique (là où Emt est maximale).

**Formule** :
$$\sigma = \sqrt{\frac{1}{n} \sum_{i=1}^{n} (x_i - \bar{x})^2}$$

avec \(n\) = nombre d’échantillons (5), \(\bar{x} = \frac{1}{n}\sum x_i\).

**ddof** : 0 (variance de population).

**Variables** : samples (5 valeurs) sur la série FIDELITY, même direction que le point critique.

**Hypothèses** : Point critique = cible et sens où l’erreur totale est maximale ; la série 5 doit être dans le même sens.

**Cas particuliers** :  
- Série 5 absente ou < 2 mesures → Ef = None → verdict indéterminé si Ef requis.  
- Si S5 capturée dans Fidélité mais non encore dans la session, ResultsProvider peut l’injecter virtuellement via `remember_fidelity` / `compute_with_fidelity`.

---

### 5.7 Détermination du point critique

**Règle** : Le point critique est la cible et le sens (montée ou descente) où l’erreur totale est maximale (en valeur absolue). En cas d’égalité, un critère secondaire (autre sens à la même cible) peut être utilisé pour départager.

---

### 5.8 Application des tolérances et verdict

Voir section 6.

---

## 6. Gestion des tolérances

### 6.1 Source des données

- **Fichier** : `{get_data_dir()}/rules/tolerances.json`
- **Chemin défaut** : `~/.EtaComp2K25/rules/tolerances.json`
- **Module de chargement** : `rules/tolerance_engine.ToleranceRuleEngine.load(path)`

### 6.2 Format attendu

```json
{
  "normale": [ { "graduation": 0.01, "course_min": 0.0, "course_max": 5.0, "Emt": 0.015, "Eml": 0.010, "Ef": 0.0015, "Eh": 0.006 } ],
  "grande": [ … ],
  "faible": [ { "graduation": 0.001, "Emt": 0.0015, "Ef": 0.0005, "Eh": 0.0006 } ],
  "limitee": [ … ]
}
```

- **Eml** : optionnel (peut être absent ou null).
- **Familles** : normale, grande, faible, limitee.
- **Course** : obligatoire pour normale/grande ; interdit pour faible/limitee.

### 6.3 Comportement si fichier absent

- Si le fichier n’existe pas : `_tol_engine = None` → pas d’évaluation de tolérances → verdict = None.
- Le calcul des erreurs reste possible.
- L’UI peut proposer une restauration des règles par défaut (depuis `tolerances.create_default_rules()`).

### 6.4 Validation et sécurisation

- **Validation à l’ouverture** : graduation > 0 ; Emt, Ef, Eh >= 0 ; Eml >= 0 si présent.
- **Familles normale/grande** : course_min <= course_max ; pas de chevauchement d’intervalles (first rule inclusive ; suivantes : min exclusive, max inclusive).
- **Familles faible/limitee** : graduation unique (pas de doublon).
- **OverlapError** : levée si plusieurs règles correspondent pour une même configuration.
- En cas d’erreur de chargement : `_tol_engine = None` pour éviter de bloquer l’UI.

### 6.5 Règle de décision (verdict)

| Condition | Verdict |
|-----------|---------|
| Aucune règle correspondante | INDETERMINE |
| Ef requise par la règle mais Ef = None | INDETERMINE |
| Une erreur mesurée > limite + 1e-9 | INAPTE |
| Toutes les erreurs <= limites | APTE |

Comparaison : `measured > limit + 1e-9` → dépassement.  
Tolérance numérique : 1e-9 mm.

---

## 7. Interface utilisateur (description fonctionnelle)

### 7.1 Onglet Session

**Contenu** :
- Opérateur, date (lecture seule), température, humidité
- Comparateur (liste déroulante + bouton « + » pour créer)
- Détenteur (liste déroulante + bouton « + »)
- Banc étalon (liste déroulante, sans banc par défaut)
- Itérations (séries), mesures/série
- Observations
- Connexion série : port, baudrate, statut
- Boutons : Nouvelle session, Charger, Enregistrer la session

**Actions** :
- Connexion/déconnexion port série
- Nouvelle session : réinitialisation
- Chargement : sélection fichier, mise à jour SessionStore
- Enregistrement : si mesures présentes, nom `{comparator_ref}_{date}.json`
- Création comparateur/détenteur à la volée : ouverture dialogue, sauvegarde, rafraîchissement

**Dépendances** : Bibliothèque comparateurs, détenteurs, bancs étalon ; SerialManager.

---

### 7.2 Onglet Mesures

**Contenu** :
- Statut (prochaine cible, cycle, sens)
- Boutons Démarrer, Arrêter, Test 3 s, Effacer
- Tableau : lignes = cycles montée + ligne moyenne ↑ + cycles descente + ligne moyenne ↓ + ligne indices ; colonnes = cibles
- Flux série (log brut), option mode debug

**Actions** :
- Démarrer : exige connexion série, au moins 2 cibles ; démarre la campagne
- Réception valeur : enregistrement dans la cellule courante, avancement automatique
- Clic cellule : mode correction (override) pour réécrire une valeur
- Arrêter : fin de campagne
- Effacer : vide tableau et store

**Règles métier** :
- Montée : cibles 0 → max ; Descente : max → 0
- Premier point montée : valeur ~0 exigée (ZERO_TOL = 1e-6)
- Valeurs prises en valeur absolue (certains bancs envoient des signes inversés)
- Mode « À la demande » : envoi d’une commande (ex. « M ») après chaque mesure
- Encodage store : readings[pos] avec pos = (cycle-1)*2 + (0 si up, 1 si down)

**Dépendances** : SessionStore, SerialManager, comparateur sélectionné pour les cibles.

---

### 7.3 Onglet Écarts de fidélité

**Contenu** :
- Rappel du déroulement (texte)
- Point critique (cible, sens)
- Tableau 5 mesures (index, valeur, horodatage)
- Stats : moyenne, écart-type ; limite Ef si règle trouvée
- Boutons : Rafraîchir, Démarrer série 5, Arrêter, Effacer, Aller à Session

**Actions** :
- Rafraîchir : recalcul à partir de la session courante
- Démarrer série 5 : capture 5 valeurs depuis le flux série
- Arrêter : fin de capture
- Effacer : suppression S5 du store

**Comportement** : Série 5 enregistrée dans SessionStore.set_fidelity. ResultsProvider peut mémoriser une capture récente (`remember_fidelity`) et l’injecter virtuellement pour le calcul même si la session n’est pas encore sauvegardée.

---

### 7.4 Onglet Courbe d’étalonnage

**Contenu** :
- Sélecteur : courbe des erreurs (µm) ou courbe des mesures (mm)
- Graphe Matplotlib : erreurs ou mesures par cible (montée/descente)
- Seuils ±Emt tracés si règle disponible
- Tableau : cible, moy ↑, moy ↓, err ↑ (µm), err ↓ (µm), hystérésis (µm)

**Actions** : Rafraîchir (recalcul depuis session courante).

**Dépendances** : ResultsProvider, get_runtime_session.

---

### 7.5 Onglet Finalisation

**Contenu** :
- Bandeau verdict (APTE / NON CONFORME / INDÉTERMINÉ)
- Tableau erreurs : Emt, Eml, Eh, Ef
- Messages détaillés (point critique, hystérésis, fidélité, règle, limites)

**Actions** :
- Calculer les erreurs : ResultsProvider.compute_all → affichage
- Exporter PDF / HTML : placeholders (message d’information uniquement)

---

### 7.6 Bibliothèque des comparateurs

**Contenu** :
- Liste des comparateurs, formulaire d’édition
- Champs : référence, fabricant, description, graduation, course, famille, périodicité, cibles (11)
- Compteur de cibles sous le champ

**Actions** : Ajouter, Éditer, Supprimer ; CRUD sur stockage.

---

### 7.7 Paramètres

Sous-onglets :
- **Général** : thème, séries/mesures par défaut, autosave, langue, dossier données
- **Règles** : édition règles par famille (normale, grande, faible, limitee)
- **Détenteurs** : CRUD détenteurs
- **Bancs étalon** : CRUD bancs, banc par défaut
- **Exports** : entité, image, titre, référence, texte normes
- **TESA ASCII** : mode envoi, commande, EOL ; regex, décimale ; frame_mode, silence_ms, eol, mask_7bit, decimals, decimal_display

---

## 8. Intégration matérielle

### 8.1 Lecture interface TESA

- **Connexion** : pyserial sur port COM
- **Paramètres** : configurés dans l’onglet Session (port, baudrate) et Paramètres > TESA ASCII

### 8.2 Paramètres série utilisés

| Paramètre | Valeur |
|-----------|--------|
| bytesize | 8 |
| parity | None |
| stopbits | 1 |
| xonxoff | False |
| rtscts | False |
| timeout | 0.05 s |

Baudrates proposés : 4800, 9600, 19200, 38400, 57600, 115200 (défaut 4800).

### 8.3 Mode « TESA » (mode bouton)

- **Assemblage de trame** : par **silence** (120 ms sans réception) ou par **EOL** (CR, LF, CRLF)
- **Masque 7-bit** : octets AND 0x7F avant interprétation
- **Strip** : suppression de \r, \n, \0, espaces en début/fin
- **Extraction** : regex `[-+]?\d+(?:[.,]\d+)?|[-+]?[.,]\d+` pour trouver un nombre
- **Décimale** : virgule remplacée par point pour le float
- **Format affichage** : 3 décimales fixes par défaut (configurable 0–6)

### 8.4 Format de trame attendu

- Ligne ou bloc de caractères ASCII contenant **un seul nombre** (avec signe et décimales)
- Exemples : `0.123`, `-0.456`, `,789` (virgule → point)
- Toute chaîne ne contenant pas de nombre valide est ignorée (log debug uniquement)

### 8.5 Interprétation des valeurs (3 digits fixes)

- **decimals** : nombre de décimales affichées (défaut 3)
- La valeur est normalisée en float, puis formatée avec ce nombre de décimales
- Affichage : point ou virgule selon `decimal_display`

### 8.6 Gestion des erreurs de lecture

- Trame sans nombre valide : ignorée, message debug
- Erreur dans on_value : signal `error.emit`
- Crash thread : `on_error` avec message
- Connexion perdue : gestion par pyserial (lecture renvoie vide ou exception)

---

## 9. Règles de robustesse

### 9.1 Gestion des erreurs

- **Chargement règles** : exception → `_tol_engine = None`, pas de blocage UI
- **Calcul** : exception → message QMessageBox, pas de plantage
- **Sauvegarde session** : `has_measures()` vérifié avant enregistrement
- **Fichiers corrompus** : comparateurs/sessions invalides ignorés silencieusement à l’énumération

### 9.2 Données manquantes

- **Comparateur non sélectionné** : pas de cibles → message « Configuration incomplète »
- **Série 5 absente** : Ef = None → verdict INDETERMINE si Ef requis
- **Règle absente** : verdict INDETERMINE avec message explicite
- **Eml absente sur règle** : critère Eml non évalué

### 9.3 Comportements sécurisés

- **Clic cellule pendant campagne** : override uniquement sur cellule déjà remplie ou sur prochaine case vide logique pour repositionner
- **Verrouillage après arrêt** : pas de modification manuelle du tableau
- **Valeur absolue** : mesures négatives converties en positif avant stockage
- **Zéro tolérant** : première mesure montée acceptée si |v| <= 1e-6
- **Injection S5** : `remember_fidelity` utilisé pour capturer S5 hors session sauvegardée ; vérification comparator_ref avant injection

---

## 10. Points critiques du système

### 10.1 Dépendances sensibles

- **Encodage readings** : `pos = (cycle-1)*2 + (0 si up, 1 si down)` doit être cohérent entre Mesures et session_adapter.
- **Limitation à 2 cycles** : session_adapter impose `cycles = min(series_count, 2)` ; au‑delà, les mesures sont ignorées.
- **Point critique** : la série 5 doit être dans le **même sens** que le point critique (montée ou descente).
- **Deux moteurs de règles** : `tolerance_engine` (verdict) et `tolerances` (UI) ; le format JSON doit rester compatible.

### 10.2 Hypothèses fortes

- **11 cibles** : format fixe ; première = 0.
- **4 séries** : S1 montée, S2 descente, S3 montée, S4 descente (2 cycles).
- **Familles** : normale, grande, faible, limitee (valeurs exactes).
- **Données** : `~/.EtaComp2K25/` ; pas de chemin personnalisable pour le dossier données.
- **Un seul banc par défaut** : unicité non vérifiée à l’échelle globale (gestion par l’UI).

### 10.3 Éléments à ne pas modifier sans impact

- Structure `readings` et mapping pos ↔ (cycle, direction)
- Formules de CalculatedResults (Emt, Eml, Eh, Ef)
- Algorithme de matching des règles (intervalles stricts, pas de chevauchement)
- Contraintes du comparateur (11 cibles, 0 obligatoire, ordre)

---

## 11. Évolutions prévues ou anticipables

### 11.1 Modularité

- **CalculationEngine** : indépendant de l’UI ; réutilisable en CLI ou API
- **SessionV2** : modèle canonique pour tests et évolutions
- **ResultsProvider** : point d’entrée unique ; alternative possible avec chargement règles externe

### 11.2 Extensions possibles

- **Export PDF/HTML** : structure ExportConfig et banc par défaut déjà en place ; génération de rapport à implémenter
- **Autosave** : préférence `autosave_enabled`, `autosave_interval_s` ; logique applicative à brancher
- **Autres familles de tolérances** : extension du dictionnaire de règles si le format le permet
- **Plus de 2 cycles** : adaptation de session_adapter et de l’affichage Mesures
- **Chemins personnalisables** : extension de `get_data_dir()` ou paramètre utilisateur

---

*Document produit à partir de l’analyse du code source. Ne décrit que les fonctionnalités effectivement implémentées.*
