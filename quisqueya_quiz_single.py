
# -*- coding: utf-8 -*-


import json
import glob
import os
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone


# ============================================================================
# MODÈLES
# ============================================================================

@dataclass
class Question:
    id: int
    theme: str
    niveau: str
    texte: str
    options: List[str]
    bonne_option: int

    def formater_pour_affichage(self, index: int, total: int) -> str:
        s = f"\nQuestion {index}/{total} [{self.theme} - {self.niveau}]\n"
        s += "─" * 60 + "\n"
        s += f"{self.texte}\n\n"
        for i, opt in enumerate(self.options, start=1):
            s += f"  {i}) {opt}\n"
        return s


# ============================================================================
# UTILITAIRES
# ============================================================================

def saisie_securisee(invite: str = "") -> str:
    """Saisie sécurisée qui gère les interruptions"""
    try:
        return input(invite)
    except (KeyboardInterrupt, EOFError):
        print("")
        return ""


def entier_securise(invite: str, val_min: Optional[int] = None, val_max: Optional[int] = None,
                    par_defaut: Optional[int] = None) -> int:
    """Demande un entier avec validation"""
    while True:
        s = saisie_securisee(invite).strip()
        if s == "" and par_defaut is not None:
            return par_defaut
        try:
            v = int(s)
            if (val_min is not None and v < val_min) or (val_max is not None and v > val_max):
                plage = []
                if val_min is not None:
                    plage.append(f">= {val_min}")
                if val_max is not None:
                    plage.append(f"<= {val_max}")
                print(f"Valeur invalide – entrez un entier {' et '.join(plage)}.")
                continue
            return v
        except ValueError:
            print("Entrée invalide – merci d'entrer un nombre entier.")


def choisir_dans_liste(elements: List[str], invite: str = "Choix (numéro) : ",
                       autoriser_zero_retour: bool = False) -> Optional[int]:
    """Affiche une liste et retourne l'index choisi"""
    if not elements:
        print("[Aucun élément disponible]")
        return None
    for idx, elem in enumerate(elements, start=1):
        print(f"{idx}) {elem}")
    if autoriser_zero_retour:
        print("0) Retour")
    while True:
        choix = saisie_securisee(invite).strip()
        if choix == "" and autoriser_zero_retour:
            return None
        try:
            n = int(choix)
            if autoriser_zero_retour and n == 0:
                return None
            if 1 <= n <= len(elements):
                return n - 1
            print("Choix hors limites. Réessaie.")
        except ValueError:
            print("Choix invalide – entrez le numéro correspondant.")


# ============================================================================
# STOCKAGE
# ============================================================================

FICHIER_SCORES = "scores.json"


class Stockage:
    """Gère la sauvegarde et le chargement des scores"""

    def __init__(self, chemin: str = FICHIER_SCORES) -> None:
        self.chemin = chemin
        if not os.path.isfile(self.chemin):
            try:
                with open(self.chemin, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
            except IOError as e:
                print(f"[Erreur] impossible de créer {self.chemin}: {e}")

    def charger_tous(self) -> List[Dict[str, Any]]:
        """Charge tous les scores"""
        try:
            with open(self.chemin, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return []

    def sauvegarder_score(self, entree: Dict[str, Any]) -> None:
        """Sauvegarde un nouveau score"""
        tous_scores = self.charger_tous()
        tous_scores.append(entree)
        temp = f"{self.chemin}.tmp"
        try:
            with open(temp, "w", encoding="utf-8") as f:
                json.dump(tous_scores, f, ensure_ascii=False, indent=2)
            os.replace(temp, self.chemin)
        except IOError as e:
            print(f"[Erreur] impossible de sauvegarder le score: {e}")

    def top_n(self, n: int = 10, theme: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retourne les n meilleurs scores"""
        tous_scores = self.charger_tous()
        if theme:
            tous_scores = [s for s in tous_scores if s.get("theme") == theme]

        def cle_tri(s: Dict[str, Any]) -> tuple:
            return (-s.get("score_total", 0), -s.get("pourcentage", 0), s.get("date_heure", ""))

        tous_scores.sort(key=cle_tri)
        return tous_scores[:n]

    def obtenir_themes_depuis_scores(self) -> List[str]:
        """Retourne tous les thèmes uniques des scores enregistrés"""
        tous_scores = self.charger_tous()
        themes = {s.get("theme") for s in tous_scores if s.get("theme")}
        return sorted(themes)

    def compter_occurrences_joueur(self, nom_joueur: str) -> int:
        """Compte combien de fois un nom de joueur apparaît dans les scores"""
        tous_scores = self.charger_tous()
        compteur = sum(1 for s in tous_scores if s.get("joueur_nom", "").lower() == nom_joueur.lower())
        return compteur

    def obtenir_stats_joueur(self, nom_joueur: str) -> Dict[str, Any]:
        """Retourne les statistiques d'un joueur"""
        tous_scores = self.charger_tous()
        scores_joueur = [s for s in tous_scores if s.get("joueur_nom", "").lower() == nom_joueur.lower()]

        if not scores_joueur:
            return {"parties": 0}

        total_parties = len(scores_joueur)
        meilleur_score = max(scores_joueur, key=lambda x: x.get("score_total", 0))
        moyenne_pourcentage = sum(s.get("pourcentage", 0) for s in scores_joueur) / total_parties

        return {
            "parties": total_parties,
            "meilleur_score": meilleur_score.get("score_total", 0),
            "meilleur_pourcentage": meilleur_score.get("pourcentage", 0),
            "moyenne_pourcentage": round(moyenne_pourcentage, 1)
        }


# ============================================================================
# BANQUE DE QUESTIONS
# ============================================================================

class BanqueQuestions:
    """Gère le chargement et la sélection des questions"""

    def __init__(self, dossier: str = "questions") -> None:
        self.questions: List[Question] = []
        self.dossier = dossier
        self._charger_questions()

    def _charger_questions(self) -> None:
        """Charge les questions depuis les fichiers JSON"""
        if os.path.isdir(self.dossier):
            motif = os.path.join(self.dossier, "*.json")
            fichiers = sorted(glob.glob(motif))
            for f in fichiers:
                self._charger_fichier(f)
        elif os.path.isfile("questions.json"):
            self._charger_fichier("questions.json")

    def _charger_fichier(self, chemin: str) -> None:
        """Charge un fichier JSON de questions"""
        try:
            with open(chemin, "r", encoding="utf-8") as f:
                donnees = json.load(f)
            if not isinstance(donnees, list):
                print(f"[Avertissement] {chemin} ne contient pas une liste de questions – ignoré.")
                return
            for element in donnees:
                if not all(k in element for k in ("id", "theme", "niveau", "texte", "options", "bonne_option")):
                    print(f"[Avertissement] entrée mal formée dans {chemin}, id approximatif: {element.get('id')}")
                    continue
                try:
                    q = Question(
                        id=int(element["id"]),
                        theme=str(element["theme"]),
                        niveau=str(element["niveau"]),
                        texte=str(element["texte"]),
                        options=list(element["options"]),
                        bonne_option=int(element["bonne_option"])
                    )
                    if not (0 <= q.bonne_option < len(q.options)):
                        print(f"[Avertissement] mauvaise bonne_option pour id {q.id} dans {chemin} – ignorée.")
                        continue
                    self.questions.append(q)
                except (ValueError, TypeError, KeyError) as e:
                    print(f"[Avertissement] impossible de créer Question depuis entrée {element.get('id')}: {e}")
        except (IOError, json.JSONDecodeError) as e:
            print(f"[Avertissement] impossible de lire {chemin}: {e}")

    def lister_themes(self) -> List[str]:
        """Retourne la liste des thèmes disponibles"""
        return sorted({q.theme for q in self.questions})

    def filtrer(self, themes: Optional[List[str]] = None,
                niveaux: Optional[List[str]] = None) -> List[Question]:
        """Filtre les questions par thème et/ou niveau"""
        resultat = self.questions
        if themes:
            resultat = [q for q in resultat if q.theme in themes]
        if niveaux:
            resultat = [q for q in resultat if q.niveau in niveaux]
        return resultat

    def echantillonner_questions(self, nombre: int = 10, themes: Optional[List[str]] = None) -> List[Question]:
        """Retourne jusqu'à nombre questions (max 10)"""
        nombre = min(int(nombre), 10)
        reserve = self.filtrer(themes, niveaux=None)
        if not reserve:
            return []

        if len(reserve) <= nombre:
            random.shuffle(reserve)
            return reserve[:nombre]
        return random.sample(reserve, nombre)



# ============================================================================
# VALIDATION NOM DU JOUEUR
# ============================================================================

def obtenir_nom_joueur(stockage: Stockage) -> Optional[str]:
    """Demande et valide le nom du joueur avec gestion des doublons"""
    while True:
        joueur = saisie_securisee("👤 Entrez votre nom ou pseudo : ").strip()

        if not joueur:
            joueur = "Joueur"

        occurrences = stockage.compter_occurrences_joueur(joueur)

        if occurrences == 0:
            print(f"\n Bienvenue {joueur} ! C'est votre première partie.\n")
            time.sleep(1)
            return joueur

        elif occurrences == 1:
            stats = stockage.obtenir_stats_joueur(joueur)
            print(f"\n️  Le nom '{joueur}' est déjà enregistré avec 1 partie.")
            print(f"   Meilleur score : {stats['meilleur_score']} points ({stats['meilleur_pourcentage']}%)")
            print("\n Êtes-vous cette même personne ?")
            print("   1) Oui, c'est moi - continuer avec ce nom")
            print("   2) Non, choisir un autre nom")
            print("   0) Annuler et retourner au menu\n")

            choix = entier_securise("➤ Votre choix : ", val_min=0, val_max=2)

            if choix == 1:
                print(f"\n Bon retour {joueur} !\n")
                time.sleep(1)
                return joueur
            elif choix == 2:
                print("\n Veuillez choisir un autre nom.\n")
                continue
            else:
                return None

        else:
            stats = stockage.obtenir_stats_joueur(joueur)
            print(f"\n️  Le nom '{joueur}' est déjà enregistré avec {occurrences} parties.")
            print(f"   Meilleur score : {stats['meilleur_score']} points ({stats['meilleur_pourcentage']}%)")
            print(f"   Moyenne : {stats['moyenne_pourcentage']}%")
            print("\n Êtes-vous cette même personne ?")
            print("   1) Oui, c'est moi - continuer avec ce nom")
            print("   2) Non, choisir un autre nom")
            print("   0) Annuler et retourner au menu\n")

            choix = entier_securise("➤ Votre choix : ", val_min=0, val_max=2)

            if choix == 1:
                print(f"\n Bon retour {joueur} ! Vous avez déjà joué {occurrences} parties.\n")
                time.sleep(1)
                return joueur
            elif choix == 2:
                print("\n Veuillez choisir un autre nom.\n")
                continue
            else:
                return None


# ============================================================================
# JEU DE QUIZ
# ============================================================================

class JeuQuiz:
    def __init__(self, questions: List[Question], nom_joueur: str, stockage: Stockage) -> None:
        self.questions = questions
        self.nom_joueur = nom_joueur
        self.stockage = stockage
        self.score = 0
        self.bonnes = 0
        self.mauvaises = 0
        self.horodatage_debut: Optional[float] = None
        self.horodatage_fin: Optional[float] = None

    def poser_question(self, q: Question, index: int, total: int) -> bool:
        """Pose une question et retourne True si on continue, False si on abandonne"""
        print("\n" + "=" * 60)
        print(q.formater_pour_affichage(index, total))
        print(" Tapez '0' ou 'Q' pour abandonner le quiz\n")

        while True:
            reponse = saisie_securisee("Ta réponse (nombre) : ")

            if reponse.strip().upper() in ['0', 'Q', 'QUIT', 'QUITTER']:
                confirmer = saisie_securisee("\n️  Voulez-vous vraiment interrompre le quiz ? (O/N) : ").strip().upper()
                if confirmer in ['O', 'OUI', 'Y', 'YES']:
                    print("\n Quiz interrompu. Retour au menu...\n")
                    time.sleep(1)
                    return False
                print("\n Continuons le quiz !\n")
                time.sleep(0.5)
                print("\n" + "=" * 60)
                print(q.formater_pour_affichage(index, total))
                print(" Tapez '0' ou 'Q' pour abandonner le quiz\n")
                continue

            try:
                choix = int(reponse.strip()) - 1
            except ValueError:
                print(f" Choix invalide ! Veuillez entrer un nombre entre 1 et {len(q.options)}.")
                time.sleep(1)
                continue

            if choix < 0 or choix >= len(q.options):
                print(f" Choix invalide ! Veuillez entrer un nombre entre 1 et {len(q.options)}.")
                time.sleep(1)
                continue

            if choix == q.bonne_option:
                print(" Bonne réponse !")
                self.bonnes += 1
                self.score += 1
            else:
                correcte = q.options[q.bonne_option] if 0 <= q.bonne_option < len(q.options) else "Inconnue"
                print(f" Mauvaise réponse. La bonne était: {correcte}")
                self.mauvaises += 1
            time.sleep(1.1)
            return True

    def jouer(self) -> Optional[Dict[str, Any]]:
        """Lance le quiz et retourne les résultats"""
        self.horodatage_debut = time.time()
        total = len(self.questions)
        print(f"\nDébut de la partie – joueur : {self.nom_joueur} – {total} questions")
        time.sleep(0.8)

        quiz_interrompu = False
        for i, q in enumerate(self.questions, start=1):
            doit_continuer = self.poser_question(q, i, total)
            if not doit_continuer:
                quiz_interrompu = True
                break

        self.horodatage_fin = time.time()
        duree = int(self.horodatage_fin - self.horodatage_debut) if self.horodatage_debut else 0

        if quiz_interrompu:
            print("\n" + "=" * 60)
            print(" QUIZ INTERROMPU")
            print("=" * 60)
            print(f"\nVous avez répondu à {self.bonnes + self.mauvaises} question(s) sur {total}")
            print(f"Bonnes réponses : {self.bonnes}")
            print("Le score n'a pas été enregistré.")
            print("\n" + "=" * 60)
            input("\nAppuie sur Entrée pour revenir au menu principal...")
            return None

        pourcentage = round((self.bonnes / total) * 100, 1) if total > 0 else 0.0
        print("\n" + "=" * 60)
        print("=== RÉSUMÉ DE LA PARTIE ===")
        print("=" * 60)
        print(f"\nJoueur : {self.nom_joueur}")
        print(f"Bonnes réponses : {self.bonnes}/{total} ({pourcentage}%)")
        print(f"Mauvaises réponses : {self.mauvaises}/{total}")
        print(f"Score total : {self.score}")
        print(f"Durée : {duree} s")

        entree: Dict[str, Any] = {
            "id_partie": f"{self.nom_joueur}_{int(time.time())}",
            "joueur_nom": self.nom_joueur,
            "date_heure": datetime.now(timezone.utc).isoformat(),
            "theme": self.questions[0].theme if len(set(q.theme for q in self.questions)) == 1 else "mix",
            "niveau": self.questions[0].niveau if len(set(q.niveau for q in self.questions)) == 1 else "mix",
            "nombre_questions": total,
            "bonnes": self.bonnes,
            "mauvaises": self.mauvaises,
            "score_total": self.score,
            "pourcentage": pourcentage,
            "duree_seconds": duree
        }
        try:
            self.stockage.sauvegarder_score(entree)
            print("\n Score enregistré avec succès !")
        except IOError as e:
            print(f"\n[Erreur] impossible de sauvegarder le score: {e}")

        print("\n" + "=" * 60)
        input("\nAppuie sur Entrée pour revenir au menu principal...")
        return entree


# ============================================================================
# APPLICATION PRINCIPALE
# ============================================================================

def ecran_bienvenue() -> None:
    """Affiche l'écran de bienvenue"""
    print("\n╔" + "═" * 60 + "╗")
    print("║" + " " * 60 + "║")
    print("║" + "     BIENVENUE DANS QUISQUEYA QUIZ SYSTÈME     ".center(60) + "║")
    print("║" + " " * 60 + "║")
    print("╚" + "═" * 60 + "╝")
    print("\n Appuyez sur [ENTRÉE] pour commencer\n")
    input()


def jouer_mode_rapide(bq: BanqueQuestions, stockage: Stockage) -> None:
    """Lance le mode rapide (10 questions aléatoires)"""
    print("\n" + "═" * 60)
    print("⚡ MODE RAPIDE - 10 QUESTIONS".center(60))
    print("═" * 60 + "\n")

    joueur = obtenir_nom_joueur(stockage)
    if joueur is None:
        return

    liste_questions = bq.echantillonner_questions(nombre=10, themes=None)
    if not liste_questions:
        print("\n Aucune question disponible.")
        input("\n Appuyez sur [ENTRÉE] pour revenir...")
        return
    print(f"\n🎮 Démarrage de la partie avec {len(liste_questions)} questions aléatoires...")
    time.sleep(1)
    jeu = JeuQuiz(liste_questions, joueur, stockage)
    jeu.jouer()


def jouer_mode_theme(bq: BanqueQuestions, stockage: Stockage) -> None:
    """Lance le mode par thème"""
    themes = bq.lister_themes()
    if not themes:
        print(" Aucun thème disponible.")
        input("Appuyez sur [ENTRÉE] pour revenir...")
        return
    print("\nSélection du thème du quiz")
    idx = choisir_dans_liste(themes, invite="➤ Choisissez un thème : ", autoriser_zero_retour=True)
    if idx is None:
        return

    joueur = obtenir_nom_joueur(stockage)
    if joueur is None:
        return

    liste_questions = bq.echantillonner_questions(nombre=10, themes=[themes[idx]])
    if not liste_questions:
        print(" Aucune question disponible pour ce thème.")
        input("Appuyez sur [ENTRÉE] pour revenir...")
        return
    jeu = JeuQuiz(liste_questions, joueur, stockage)
    jeu.jouer()


def afficher_classement(bq: BanqueQuestions, stockage: Stockage) -> None:
    """Affiche le classement des meilleurs scores"""
    print("\n" + "═" * 60)
    print(" CLASSEMENT DES MEILLEURS SCORES".center(60))
    print("═" * 60 + "\n")

    n = entier_securise(
        " Combien de scores voulez-vous voir ? (1-50, défaut: 10) : ",
        val_min=1, val_max=50, par_defaut=10
    )

    themes_questions = bq.lister_themes()
    themes_scores = stockage.obtenir_themes_depuis_scores()
    tous_themes = sorted(set(themes_questions + themes_scores))

    print("\n" + "─" * 60)
    print(" FILTRER PAR THÈME")
    print("─" * 60 + "\n")

    if not tous_themes:
        print(" Aucun thème disponible.")
        theme = None
    else:
        options_theme = ["Tous les thèmes"] + tous_themes
        print("Thèmes disponibles :\n")
        idx = choisir_dans_liste(
            options_theme,
            invite="➤ Choisissez un thème (ou 0 pour annuler) : ",
            autoriser_zero_retour=True
        )

        if idx is None:
            return

        theme = None if idx == 0 else tous_themes[idx - 1]

    top = stockage.top_n(n, theme)

    print("\n" + "─" * 60)
    if not top:
        print("\n Aucun score enregistré pour le moment.")
        print("   Jouez une partie pour apparaître dans le classement !")
    else:
        print(f" Thème : {theme}" if theme else " Tous les thèmes")
        print("─" * 60 + "\n")
        for i, s in enumerate(top, start=1):
            pourc_str = f"{s.get('pourcentage', 'N/A')}%"
            medaille = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            print(f"{medaille} {s.get('joueur_nom')}")
            print(f"   Score : {s.get('score_total')} points")
            print(f"   Réussite : {s.get('bonnes')}/{s.get('nombre_questions')} ({pourc_str})")
            print(f"   Date : {s.get('date_heure', '')[:10]}")
            print(f"   Thème : {s.get('theme')}\n")
    print("─" * 60)
    input("\n Appuyez sur [ENTRÉE] pour revenir au menu principal...")


def instructions() -> None:
    """Affiche les instructions du jeu"""
    print("\n" + "═" * 60)
    print(" INSTRUCTIONS & AIDE".center(60))
    print("═" * 60 + "\n")
    print(" COMMENT JOUER ?\n")
    print("   • Une partie contient jusqu'à 10 questions")
    print("   • Chaque bonne réponse vaut 1 point")
    print("   • Choisissez votre réponse en tapant le numéro correspondant\n")
    print(" SCORES\n")
    print("   • Vos scores sont sauvegardés automatiquement")
    print("   • Consultez le classement dans le menu principal\n")
    print(" MODES DE JEU\n")
    print("   • Mode Rapide : 10 questions, tous thèmes")
    print("   • Mode Thème : choisissez un thème spécifique\n")
    print(" NAVIGATION\n")
    print("   • Tapez le numéro de l'option souhaitée")
    print("   • '0' permet de revenir en arrière\n")
    print(" ASTUCES\n")
    print("   • Lisez bien chaque question avant de répondre")
    print("   • Vos statistiques sont suivies dans le classement\n")
    print("═" * 60)
    input("\n Appuyez sur [ENTRÉE] pour revenir au menu...")


def principal() -> None:
    """Point d'entrée principal du programme"""
    bq = BanqueQuestions(dossier="questions")
    stockage = Stockage()

    if not bq.questions:
        print("\n️ Aucune question trouvée dans le dossier 'questions/'")
        print("Veuillez ajouter des fichiers JSON de questions.")
        input("\nAppuyez sur [ENTRÉE] pour quitter...")
        return

    ecran_bienvenue()

    while True:
        try:
            print("\n" + "╔" + "═" * 58 + "╗")
            print("║" + " QUISQUEYA QUIZ SYSTÈME  - MENU PRINCIPAL ".center(58) + "║")
            print("╚" + "═" * 58 + "╝\n")

            options = [
                " Jouer",
                " Classement / Scores",
                " Instructions / Aide",
                " Quitter"
            ]

            for i, opt in enumerate(options, start=1):
                print(f"   {i}) {opt}")
            print("\n" + "─" * 60)

            choix = entier_securise("➤ Votre choix (1-4) : ", val_min=1, val_max=4)

            if choix == 1:
                while True:
                    try:
                        print("\n" + "╔" + "═" * 58 + "╗")
                        print("║" + " MENU JOUER".center(58) + "║")
                        print("╚" + "═" * 58 + "╝\n")
                        print("   1) ⚡ Mode rapide (10 questions)")
                        print("   2)  Mode par thème")
                        print("   0) ← Retour au menu principal\n")
                        print("─" * 60)

                        sous = entier_securise("➤ Votre choix : ", val_min=0, val_max=2, par_defaut=0)
                        if sous == 0:
                            break
                        if sous == 1:
                            jouer_mode_rapide(bq, stockage)
                        elif sous == 2:
                            jouer_mode_theme(bq, stockage)
                    except KeyboardInterrupt:
                        print("\n\n Opération annulée.")
                        input("\n Appuyez sur [ENTRÉE] pour continuer...")
                        break
                    except (IOError, ValueError) as e:
                        print(f"\n Erreur inattendue : {e}")
                        input("\n Appuyez sur [ENTRÉE] pour continuer...")

            elif choix == 2:
                afficher_classement(bq, stockage)
            elif choix == 3:
                instructions()
            elif choix == 4:
                sur = saisie_securisee("❓ Êtes-vous sûr de vouloir quitter ? (O/N) : ").strip().lower().startswith("o")
                if sur:
                    print("\n" + "═" * 60)
                    print(" Merci d'avoir joué à Quisqueya Quiz Système  !".center(60))
                    print("À bientôt ! ".center(60))
                    print("═" * 60 + "\n")
                    break

        except KeyboardInterrupt:
            print("\n\n Opération annulée.")
            input("\n Appuyez sur [ENTRÉE] pour continuer...")
        except (IOError, ValueError) as e:
            print("\n" + "─" * 60)
            print(f" [Erreur inattendue] {e}")
            print("─" * 60)
            input("\n Appuyez sur [ENTRÉE] pour revenir au menu principal...")


if __name__ == "__main__":
    principal()