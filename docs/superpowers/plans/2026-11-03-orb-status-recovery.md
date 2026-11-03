# ORB : panne du statut et position du 3 novembre

Autorisation : recuperer la position shadow avec les donnees manquantes, garder le journal et tous les parametres, puis relancer meme apres 09:30.

1. Sauvegarde SQLite coherente, verification du lanceur arrete et absence de STOP. Acquisition SIP QQQ en GET uniquement, donnees et preuves privees dans runtime/recovery.
2. Tests reproduisant le verrou Windows du statut et la reprise d'une position deja entree. Corriger uniquement la telemetrie ORB ; aucune modification du moteur historique, des couts ou de Noise Area.
3. Preparer la reprise sur copie avec l'entree, la quantite et les barres connues conservees. Refuser une reprise toujours lacunaire. Transaction gardee par empreinte et verrou d'instance ; evenement d'audit, jamais de promotion prospective ni double frais.
4. Verification et revue, appliquer la reprise autorisee, relancer la tache fixe shadow puis verifier plusieurs cycles reels. Publier le rapport et les tests, sans secret ni journal prive.
