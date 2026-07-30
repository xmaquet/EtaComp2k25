# Déploiement EtaComp2K25 sur Ubuntu Desktop 26.04

Guide pas à pas pour un PC Ubuntu Desktop déjà installé. Aucune connaissance Linux préalable requise.

> **Prérequis :** Ubuntu 26.04 Desktop fonctionnel sur le PC cible (disque dur opérationnel, session utilisateur accessible).

---

## Sommaire

1. [Ce que vous allez obtenir](#1-ce-que-vous-allez-obtenir)
2. [Matériel et prérequis](#2-matériel-et-prérequis)
3. [Phase 1 — Vérifier Ubuntu](#phase-1--vérifier-ubuntu)
4. [Phase 2 — Déployer EtaComp2K25](#phase-2--déployer-etacomp2k25)
5. [Phase 3 — Configurer le port série TESA](#phase-3--configurer-le-port-série-tesa)
6. [Phase 4 — Validation](#phase-4--validation)
7. [Mise à jour de l'application](#mise-à-jour-de-lapplication)
8. [Dépannage](#dépannage)

---

## 1. Ce que vous allez obtenir

| Élément | Emplacement | Rôle |
|---------|-------------|------|
| Code source (Git) | `~/EtaComp2k25/` | Stockage + mises à jour via GitHub |
| Environnement Python | `~/EtaComp2k25/.venv/` | Exécution isolée de l'application |
| Données métier | `~/.EtaComp2K25/` | Sessions, comparateurs, PDF exportés |
| Raccourci bureau | **EtaComp2K25** sur le Bureau + menu Applications | Lancement en un clic |

Le profil utilisateur démarre **vide** (pas de comparateurs pré-chargés).

---

## 2. Matériel et prérequis

- PC cible avec **Ubuntu 26.04 Desktop** déjà installé et démarrable
- Connexion Internet (Wi‑Fi ou câble Ethernet)
- Câble **RS-232 → USB** (adaptateur série, déjà testé)

**Branche GitHub utilisée :** `main` (contient stabilisation v1.0.1 + correctifs post-fusion).

> **Note sur les branches :** la branche `stabilisation/v1.0.1` a été fusionnée dans `main` (PR #15). `main` contient 3 correctifs supplémentaires, dont la libération du port COM — important pour votre adaptateur RS-232 USB. Le script déploie donc `main` par défaut.

---

## Phase 1 — Vérifier Ubuntu

1. Allumez le PC et connectez-vous avec votre mot de passe.
2. Si Ubuntu propose des mises à jour : cliquez **Installer maintenant** (recommandé).
3. Ouvrez le **Terminal** :
   - Raccourci : **Ctrl + Alt + T**
   - Ou : touche Super (Windows) → tapez « Terminal » → Entrée

4. Vérifiez Internet :

```bash
ping -c 3 ubuntu.com
```

Vous devez voir `3 packets transmitted, 3 received`. Ctrl+C pour arrêter si besoin.

5. Vérifiez Python :

```bash
python3 --version
```

Résultat attendu : `Python 3.12.x` ou supérieur.

6. (Optionnel) Vérifiez la version Ubuntu :

```bash
lsb_release -d
```

Résultat attendu : `Ubuntu 26.04 LTS`.

✅ **Ubuntu est prêt pour le déploiement.**

---

## Phase 2 — Déployer EtaComp2K25

### 2.1 — Télécharger le script d'installation

Dans le Terminal :

```bash
mkdir -p ~/EtaComp2k25
cd ~/EtaComp2k25
git clone --branch main --single-branch https://github.com/xmaquet/EtaComp2k25.git .
chmod +x scripts/deploy/ubuntu_install.sh
```

> Si le dossier existe déjà (relance) : `cd ~/EtaComp2k25 && git pull`

### 2.2 — Lancer l'installation

```bash
bash scripts/deploy/ubuntu_install.sh
```

Le script va :
- installer les paquets système (git, Python, librairies Qt…)
- cloner/mettre à jour le dépôt GitHub
- créer l'environnement Python `.venv`
- installer l'application (`pip install -e ".[dev]"`)
- créer le raccourci **EtaComp2K25** sur le **Bureau** et dans le menu Applications
- ajouter votre utilisateur au groupe **dialout** (port série)

**Durée :** 5–15 minutes selon la connexion.

### 2.3 — Redémarrer la session (important pour le port série)

Après l'installation, **déconnectez-vous puis reconnectez-vous** (ou redémarrez) pour activer le groupe `dialout`.

Menu en haut à droite → icône utilisateur → **Se déconnecter** → reconnectez-vous.

### 2.4 — Lancer l'application

**Méthode 1 — Bureau :**
- Double-cliquez sur **EtaComp2K25** sur le Bureau (`~/Bureau/`)

> Si Ubuntu demande « Autoriser le lancement » au premier clic : clic droit → **Autoriser le lancement**.

**Méthode 2 — Menu :**
- Touche Super → tapez `EtaComp` → cliquez **EtaComp2K25**

**Méthode 3 — Terminal :**

```bash
~/EtaComp2k25/.venv/bin/etacomp
```

L'application doit s'ouvrir en plein écran.

---

## Phase 3 — Configurer le port série TESA

Votre adaptateur **RS-232 → USB** apparaît sous Linux comme `/dev/ttyUSB0` (ou `ttyUSB1`, etc.).

### 3.1 — Brancher le câble

1. Branchez l'adaptateur USB sur le PC Ubuntu.
2. Branchez le côté RS-232 sur le comparateur TESA.

### 3.2 — Identifier le port

```bash
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

Exemple de résultat : `/dev/ttyUSB0`

Pour voir le nom du périphérique :

```bash
dmesg | tail -20
```

Cherchez une ligne contenant `ttyUSB` et le nom du chip (FTDI, Prolific, CH340…).

### 3.3 — Tester la communication (sonde)

```bash
~/EtaComp2k25/.venv/bin/python ~/EtaComp2k25/src/etacomp/tools/serial_probe.py /dev/ttyUSB0
```

Remplacez `/dev/ttyUSB0` par votre port. Le baud par défaut est **4800** (standard TESA).

Si des lignes `LIGNE: '...'` apparaissent → le câble fonctionne.

### 3.4 — Configurer dans l'application

1. Lancez **EtaComp2K25**.
2. Onglet **Session** (ou barre de connexion série).
3. Sélectionnez le port `/dev/ttyUSB0`.
4. Baud : **4800** (sauf indication contraire sur votre appareil).
5. Cliquez **Connecter**.
6. Paramètres avancés TESA : menu **Paramètres** si besoin (protocole ASCII, silence_ms, etc.).

La configuration est sauvegardée dans `~/.EtaComp2K25/tesa_config.json`.

---

## Phase 4 — Validation

Checklist minimale :

- [ ] L'application démarre sans erreur
- [ ] Les onglets Bibliothèques, Session, Mesures s'affichent
- [ ] Création d'un comparateur test dans Bibliothèques
- [ ] Création d'une session test
- [ ] (Si TESA branché) connexion série OK + valeur reçue
- [ ] Export PDF depuis Finalisation

---

## Mise à jour de l'application

Quand une nouvelle version est publiée sur GitHub :

```bash
cd ~/EtaComp2k25
git pull
.venv/bin/pip install -e ".[dev]"
```

Relancez l'application.

---

## Dépannage

### « Permission denied » sur `/dev/ttyUSB0`

```bash
groups
```

Vous devez voir `dialout` dans la liste. Sinon :

```bash
sudo usermod -aG dialout $USER
```

Puis **déconnexion/reconnexion**.

### L'application ne s'ouvre pas (erreur Qt / libxcb)

Relancez le script d'installation (il réinstalle les librairies manquantes) :

```bash
bash ~/EtaComp2k25/scripts/deploy/ubuntu_install.sh
```

### Erreur `libxcb-cursor.so.0: cannot open shared object file`

```bash
sudo apt install libxcb-cursor0
```

### Le port série n'apparaît pas

- Vérifiez le câble USB (autre port USB).
- `dmesg | tail -30` après branchement.
- Certains adaptateurs Prolific/CH340 nécessitent un pilote : sous Ubuntu 26.04, ils sont en général inclus.

### `git pull` échoue (conflits locaux)

Ne modifiez pas les fichiers dans `~/EtaComp2k25/` manuellement. En cas de conflit :

```bash
cd ~/EtaComp2k25
git stash
git pull
```

### Réinstallation propre

```bash
rm -rf ~/EtaComp2k25
# Conserver les données métier : ~/.EtaComp2K25/ n'est PAS supprimé
bash -c "$(curl -fsSL https://raw.githubusercontent.com/xmaquet/EtaComp2k25/main/scripts/deploy/ubuntu_install.sh)"
```

*(Ou recloner manuellement comme en Phase 2.)*

---

## Structure finale sur le disque

```
/home/<utilisateur>/
├── EtaComp2k25/                 ← dépôt Git (sources)
│   ├── .venv/                   ← Python + dépendances
│   ├── src/etacomp/             ← code application
│   ├── scripts/deploy/          ← script d'installation
│   └── ...
└── .EtaComp2K25/                ← données utilisateur (créé au 1er lancement)
    ├── comparators/
    ├── sessions/
    ├── exports/
    ├── config.json
    └── tesa_config.json
```

---

## Référence rapide

| Action | Commande |
|--------|----------|
| Lancer l'app | `~/EtaComp2k25/.venv/bin/etacomp` |
| Mettre à jour | `cd ~/EtaComp2k25 && git pull && .venv/bin/pip install -e ".[dev]"` |
| Lister ports série | `ls /dev/ttyUSB*` |
| Sonde série | `~/EtaComp2k25/.venv/bin/python ~/EtaComp2k25/src/etacomp/tools/serial_probe.py /dev/ttyUSB0` |
| Logs Python | Lancer depuis le terminal pour voir les messages |

---

*Document v1.1 — Ubuntu 26.04 Desktop (déjà installé) — EtaComp2K25 v1.0.1*
