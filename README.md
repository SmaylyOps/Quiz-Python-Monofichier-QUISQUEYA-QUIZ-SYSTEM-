Quisqueya Système Quiz 🎓

Application console interactive de quiz développée en Python.

📌 Présentation

Quisqueya Système Quiz est une application CLI (Command Line Interface) permettant de tester ses connaissances à travers des questions à choix multiples organisées par thèmes.

Le projet inclut :

un système de score automatique,

un classement des meilleurs joueurs,

une gestion persistante des données via JSON.

🚀 Fonctionnalités

Quiz interactif en console

Mode rapide (10 questions aléatoires)

Mode par thème

Sauvegarde automatique des scores

Classement avec top N joueurs

Statistiques par joueur

Aucune dépendance externe

🛠️ Technologies

Langage : Python 3.7+

Interface : CLI

Stockage : JSON

Librairies : Bibliothèque standard Python uniquement

📂 Structure du projet
.
├── quisqueya_quiz_single.py
├── questions/
│   └── questions.json
└── scores.json

▶️ Installation & Exécution



Se placer dans le dossier :

cd quisqueya-systeme-quiz


Lancer l’application :

python quisqueya_quiz_single.py

🧠 Fonctionnement

Les questions sont chargées depuis des fichiers JSON

Chaque partie contient jusqu’à 10 questions

Les réponses sont saisies via le clavier

Les scores sont enregistrés automatiquement

🧪 Exemple de question
Question 1/10 [Histoire - Moyen]

Qui a proclamé l’indépendance d’Haïti en 1804 ?

1) Toussaint Louverture
2) Dessalines
3) Henri Christophe
4) Pétion

🏆 Classement

Tri par score et pourcentage

Filtrage possible par thème

Médailles pour le top 3

⚠️ Limitations

Interface uniquement en ligne de commande

Pas de mode multijoueur

Pas d’interface graphique

📄 Licence

Projet éducatif libre d’utilisation à des fins académiques et personnelles.

👤 Auteur

Smayly Chrislend DUMEZIL,
Jorguino MARCELIN
Université Quisqueya
