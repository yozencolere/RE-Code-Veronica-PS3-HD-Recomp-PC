# Fork perso — récapitulatif des modifications

Fork de **RE Code Veronica PS3 HD Recomp PC** de Kastiel
([kastieloficial/RE-Code-Veronica-PS3-HD-Recomp-PC](https://github.com/kastieloficial/RE-Code-Veronica-PS3-HD-Recomp-PC), licence MIT),
à partir de la version **v1.5.3**. Toutes les modifications ci-dessous sont dans un commit posé sur le tag `v1.5.3`
d'origine : `git diff v1.5.3` les montre en entier.

Usage visé : version **US (NPUB30467)** avec les **textes européens en français** (copie EU NPEB00553) superposés,
sur Windows, en version **sans console**.

Comme dans le dépôt d'origine, rien du jeu n'est publié : ni le code recompilé (`src/recomp_us`, à régénérer
localement), ni les fichiers du jeu, ni les textures extraites ou agrandies.

---

## 1. Lancer le jeu directement

- Option **« Lancer le jeu directement »** (clé `enhancements/direct_start` du fichier `cv_launcher.ini`) :
  le launcher ne s'affiche plus, le jeu démarre tout de suite. **Maj** maintenue au démarrage = launcher visible.
- Pas de relance du launcher à la fermeture du jeu.
- Vérification automatique et bouton manuel des mises à jour retirés.
- `Code Veronica.exe` lance directement l'exe US s'il existe (au lieu de passer par l'exe EU).
- Fichiers : `projects/code_veronica/launcher.cpp`, `launcher_i18n.h`, `distribution/launcher_entry.cpp`, `main.cpp`.

## 2. Quitter vers Windows depuis le menu OPTIONS

- Dans le menu OPTIONS ouvert par **Start** en jeu, sur la ligne **QUITTER** : un premier appui sur Croix affiche
  « VERS WINDOWS ? (CONFIRMER) » à droite, un second ferme le jeu. Bouger le curseur ou Rond annule.
- Textes en français, anglais et portugais.
- Fichier : `projects/code_veronica/cv_appearance_menu.cpp`.

## 3. Textes européens en français dans la version US

- **Espacement des lettres** : l'exe US n'a que la table de largeurs anglaise ; le français de l'exe EU utilise
  une autre table (espace de 16 au lieu de 14). La table EU (162 valeurs) est copiée sur la table US au chargement.
  `CV_EU_TEXT_METRICS=0` pour comparer avec l'original.
  Fichiers : `cv_eu_text_metrics.h`, `cv_eu_text_metrics_data.h`, appel dans `main.cpp`.
- **Accents (é, è, à…)** : le code US envoyait les caractères au-delà du n° 108 vers les kanji ; le seuil passe à
  162 quand les textes EU sont actifs. Le correctif se fait sur le code recompilé par le script
  `tools/cv_fork_glyph_limit.py` (idempotent, **à relancer si `src/recomp_us` est régénéré**).
- **Constantes de mise en page** EU appliquées (espaces 14→16, 20→16, 68→64). `CV_EU_LAYOUT=0` pour comparer.

## 4. Bug de la porte (personnage décalé de 2 m en revenant de la salle rm_0010)

- Présent avant le fork, absent en anglais. Cause : à la préparation des archives traduites, toute l'archive était
  réencodée ; la table des positions d'entrée de rm_0010 (48 octets, stockée brute) compressée faisait aussi
  48 octets, et le jeu (qui lit brut quand taille stockée = taille réelle) lisait alors des données zlib comme des
  positions.
- Correctif : `rewrite_archive()` recopie chaque entrée d'origine à l'octet près et ne réécrit que les messages
  traduits (compressés seulement si c'est plus petit), avec autovérification (sinon l'archive US d'origine est
  gardée). Cache passé de v3 à v4.
- Fichiers : `projects/code_veronica/cv_native_language.cpp`, test étendu `tests/test_native_language.cpp`
  (16 combinaisons, toutes réussies). Script de test : `_build/build_test_langue.cmd`.

## 5. Traits verticaux et lignes parasites dans l'inventaire

- Cause : chaque élément d'interface est un rectangle de 6 sommets ; le filtrage bilinéaire allait lire les texels
  voisins dans l'atlas (ex. : la colonne noire au bord de la page d'icônes).
- Correctif : pour 10 atlas d'interface reconnus par leur empreinte, le shader de lecture des sommets
  (`vf_wrap_vs`) rentre les coordonnées de texture d'un demi-texel vers l'intérieur du rectangle.
  Fonctionne avec `RSX_GPU_VFETCH=1` (option « vertices sur le GPU »).
- Réglages : `CV_UV_INSET=0` pour couper, `CV_UV_INSET_TEXTURES` / `CV_NEAREST_TEXTURES` pour ajouter des textures.
  Diagnostic (build console) : `CV_NEAREST_DUMP=<fichier>`.
- Fichier : `libs/video/rsx_d3d12_backend.c`.

## 6. Logo MT FRAMEWORK retiré au lancement

- Les logos du démarrage sont une seule animation (avertissements, CAPCOM aux images 560-699, MT FRAMEWORK aux
  images 700-819). Dès qu'elle atteint MT FRAMEWORK, elle est terminée : seul CAPCOM s'affiche.
- `CV_SKIP_MT_LOGO=0` pour garder le logo. L'option existante `cv_skip_logos` saute toujours tout.
- Fichier : `projects/code_veronica/boot_skip.cpp`.

## 7. Animations de porte à 60 FPS

- En mode 60 FPS, le jeu calcule 30 images par seconde et le portage interpole une image sur deux, mais seulement
  dans les salles : pendant une porte, chaque image était affichée deux fois (rendu à 30 FPS).
- Pendant une porte, `func_0003B810` (US) anime et dessine la scène de porte, objet `0x00CA72F0` : caméra
  (+0x58/+0x5C/+0x60, angles +0x70/+0x74/+0x78), fondu (+0x3C), modèle de la porte (+0xC4, arbre de pièces
  avec position / rotation / échelle).
- Sur l'image intermédiaire, une mise à jour du jeu de plus tourne avec la porte en pause (bit 0x80 de +0x08 :
  la routine ne fait que dessiner, sans faire avancer quoi que ce soit ni demander de son), la caméra, le fondu
  et les pièces de la porte placés une demi-image plus loin ; ensuite ces valeurs et le chronomètre de partie
  sont remis comme avant. (Dessiner la porte hors d'une mise à jour bloque son moteur de rendu de modèles.)
- `CV_DOOR_SMOOTH=0` remet les portes d'origine ; `CV_DOOR_LOG=1` écrit `door-log.txt` et `door60-log.txt`.
- Fichier : `projects/code_veronica/cv_fps_experimental.cpp` (version US seulement).

## 8. Cinématiques du moteur à 60 FPS

- Les cinématiques calculées par le moteur (pas les vidéos `.pam`) tournent avec le mode caméra `0x4` et le bit
  de contrôle « script » : l'interpolation des salles les excluait, elles restaient à 30 FPS.
- `native_scene_ready()` accepte maintenant ce mode, comme les escaliers et événements scriptés déjà gérés
  (mêmes garde-fous : changements de plan, chargements, messages).
- Les bandes noires (`func_00190010`, appelée par le dessin de scène quand leur opacité à système+0x2A644 est
  positive) sont redessinées sur l'image reconstruite ; sinon elles disparaissaient hors sous-titres.
- `CV_SMOOTH_CUTSCENES=0` remet les cinématiques d'origine, `CV_SMOOTH_CUTSCENE_BARS=0` coupe le redessin des
  bandes. Fichier : `projects/code_veronica/cv_smooth_animation.h` (bandes : version US).

## 9. Version sans fenêtre console

- `_build/build_us_dist.cmd` produit l'exe US en sous-système Windows (aucune fenêtre cmd) et `Code Veronica.exe`.
  `_build/build_us.cmd` produit la version console (utile pour les diagnostics).

## 10. Diagnostic des appuis de touches

- `CV_PAD_TRACE=1` journalise les appuis reçus (a servi à montrer que les doubles entrées venaient de l'option
  « Confirmation améliorée », pas de la manette). Fichier : `libs/input/cellPad.c`.

---

## Compilation

1. `1_INSTALLER_ET_COMPILER.cmd` (ou `_build/installer_et_compiler.ps1`) installe les outils et compile.
2. Régénérer le code recompilé à partir de **votre** exe du jeu (voir le README d'origine), puis lancer
   `python tools/cv_fork_glyph_limit.py` pour le correctif des accents. Pour la version US, le dossier SPU se
   génère avec `python tools/cv_make_spu_us.py <EBOOT.elf US>` (mêmes images SPU que l'EU, adresses décalées).
3. Variables attendues par les scripts `_build/*.cmd` : `CV_SRC`, `CV_TOOLS`, `CV_PYTHON`, `CV_JOBS`.

## Outils d'analyse (`_build/outils_fork`)

Scripts Python / PowerShell écrits pendant le travail : lecture des archives `.arc` et des textures XET
(`compare_arc.py`, `extrait_icones.py`, `extrait_menus_x4.py`, `index_textures.py`, `texhash.py` = empreinte des
textures comme le jeu la calcule), reconstitution et mesure des dessins de l'inventaire (`quads_dump.py`,
`rendu_tri.py`, `crop_bmp.py`), tables de largeurs (`tables_largeurs.py`), lecture de la mémoire du jeu
(`memoire_jeu.py`), pilotage clavier pour les tests (`pilote.ps1`, `vers_jeu.ps1`, `vers_inventaire.ps1`).
Le script de déchiffrement de l'exe n'est pas publié.
