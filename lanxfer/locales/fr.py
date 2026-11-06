"""Français (vouvoiement). 0 et 1 sont au singulier."""

MESSAGES = {
    # Window
    "Settings": "Paramètres",
    "Light or dark appearance": "Apparence claire ou sombre",
    "Light": "Clair",
    "Dark": "Sombre",
    "Auto": "Auto",
    "Same as system": "Comme le système",
    "This computer: <b>{name}</b>": "Cet ordinateur : <b>{name}</b>",
    "All addresses: {addresses}": "Toutes les adresses : {addresses}",
    "no network connection": "pas de connexion réseau",
    "Choose the computer to send to": "Choisissez l’ordinateur destinataire",
    "Add computer by IP address…": "Ajouter un ordinateur par adresse IP…",
    "Choose files and folders": "Choisissez les fichiers et dossiers",
    "Drag files or folders here\n\nor use the buttons below":
        "Faites glisser des fichiers ou des dossiers ici\n\nou utilisez les boutons ci-dessous",
    "Add files…": "Ajouter des fichiers…",
    "Add folder…": "Ajouter un dossier…",
    "Remove": "Retirer",
    "Clear": "Vider",
    "Send": "Envoyer",
    "Send {n} item to {name}": ("Envoyer {n} élément à {name}", "Envoyer {n} éléments à {name}"),
    "Choose a computer and add some files first.": "Choisissez d’abord un ordinateur et ajoutez des fichiers.",
    "Transfers": "Transferts",
    "Nothing sent or received yet.": "Rien n’a encore été envoyé ni reçu.",
    "Received files are saved in:  {folder}": "Les fichiers reçus sont enregistrés dans :  {folder}",
    "Change…": "Modifier…",
    "Open": "Ouvrir",
    "folder": "dossier",
    "Choose files to send": "Choisir les fichiers à envoyer",
    "Choose a folder to send": "Choisir un dossier à envoyer",
    "Save received files in": "Enregistrer les fichiers reçus dans",
    "This computer cannot receive files right now:\n{error}\n\nSending still works.":
        "Cet ordinateur ne peut pas recevoir de fichiers pour le moment :\n{error}\n\nL’envoi fonctionne toujours.",

    # Computers list
    "Looking for other computers…": "Recherche d’autres ordinateurs…",
    "No other computers found yet.\n\nOpen {app} on the other computer and make sure both are on the same Wi-Fi."
    "\n\nIf a firewall question pops up, click Allow.":
        "Aucun autre ordinateur trouvé pour l’instant.\n\nOuvrez {app} sur l’autre ordinateur et vérifiez que les "
        "deux sont sur le même Wi-Fi.\n\nSi le pare-feu pose une question, cliquez sur Autoriser.",
    "Use “Add computer by IP address…” instead.": "Utilisez plutôt « Ajouter un ordinateur par adresse IP… ».",
    "Automatic discovery is unavailable (UDP port {port}: {error}).":
        "La recherche automatique n’est pas disponible (port UDP {port} : {error}).",
    "Version {version}": "Version {version}",
    "Older version": "Version plus ancienne",
    "update ready": "mise à jour prête",
    "Send files to {name}": "Envoyer des fichiers à {name}",
    "Update to version {version}": "Mettre à jour vers la version {version}",
    "Forget this computer": "Oublier cet ordinateur",
    "Add computer by IP address": "Ajouter un ordinateur par adresse IP",
    "Type the IP address shown at the top of {app} on the other computer\n(for example 192.168.1.42):":
        "Saisissez l’adresse IP affichée en haut de {app} sur l’autre ordinateur\n(par exemple 192.168.1.42) :",
    "“{text}” is not a valid IP address.": "« {text} » n’est pas une adresse IP valide.",
    "Could not reach {address}.\n\nCheck that {app} is open on that computer, that both computers are on the "
    "same network, and that its firewall allows the app.":
        "Impossible de joindre {address}.\n\nVérifiez que {app} est ouvert sur cet ordinateur, que les deux "
        "ordinateurs sont sur le même réseau et que le pare-feu autorise l’application.",

    # Transfer rows
    "Cancel": "Annuler",
    "Open folder": "Ouvrir le dossier",
    "Remove from list": "Retirer de la liste",
    "Sending “{item}” to {name}": "Envoi de « {item} » à {name}",
    "Sent “{item}” to {name}": "« {item} » envoyé à {name}",
    "Sending {n} item to {name}": ("Envoi de {n} élément à {name}", "Envoi de {n} éléments à {name}"),
    "Sent {n} item to {name}": ("{n} élément envoyé à {name}", "{n} éléments envoyés à {name}"),
    "Receiving “{item}” from {name}": "Réception de « {item} » de {name}",
    "Received “{item}” from {name}": "« {item} » reçu de {name}",
    "Receiving {n} item from {name}": ("Réception de {n} élément de {name}", "Réception de {n} éléments de {name}"),
    "Received {n} item from {name}": ("{n} élément reçu de {name}", "{n} éléments reçus de {name}"),
    "Updating {name} to version {version}": "Mise à jour de {name} vers la version {version}",
    "Updated {name} to version {version}": "{name} mis à jour vers la version {version}",
    "Receiving version {version} from {name}": "Réception de la version {version} depuis {name}",
    "Installed version {version} from {name}": "Version {version} installée depuis {name}",
    "Starting": "Démarrage",
    "{done} of {total}": "{done} sur {total}",
    "about {time} left": "encore environ {time}",
    "file {current} of {total}": "fichier {current} sur {total}",
    "{size} in {time}": "{size} en {time}",
    "Done": "Terminé",
    "Failed": "Échec",
    "Cancelled": "Annulé",
    "Declined": "Refusé",
    "{n} file": ("{n} fichier", "{n} fichiers"),

    # Incoming files
    "Incoming files": "Fichiers entrants",
    "<b>{name}</b> ({os} · {ip}) wants to send you {files} ({size}).":
        "<b>{name}</b> ({os} · {ip}) veut vous envoyer {files} ({size}).",
    "{name}   —   folder, {files}, {size}": "{name}   —   dossier, {files}, {size}",
    "They will be saved in a new numbered folder inside: {folder}":
        "Ils seront enregistrés dans un nouveau dossier numéroté, dans : {folder}",
    "⚠ Not enough free space: only {size} available.": "⚠ Espace libre insuffisant : seulement {size} disponibles.",
    "Accept": "Accepter",
    "Decline": "Refuser",
    "Declines automatically in {seconds} s": "Refus automatique dans {seconds} s",

    # Settings
    "Name of this computer:": "Nom de cet ordinateur :",
    "Save received files in:": "Enregistrer les fichiers reçus dans :",
    "Browse…": "Parcourir…",
    "Ask me before accepting incoming files (recommended)":
        "Me demander avant d’accepter des fichiers entrants (recommandé)",
    "Appearance:": "Apparence :",
    "Language:": "Langue :",
    "Automatic (system language)": "Automatique (langue du système)",
    "IP address: {ip}": "Adresse IP : {ip}",
    "not connected": "non connecté",
    "Port: {port}": "Port : {port}",
    "not listening": "pas à l’écoute",
    "The new language is used after {app} restarts. Restart now?":
        "La nouvelle langue sera utilisée après le redémarrage de {app}. Redémarrer maintenant ?",

    # Updates
    "Update": "Mettre à jour",
    "Update {name}": "Mettre à jour {name}",
    "Update all ({n})": "Tout mettre à jour ({n})",
    "Restart now": "Redémarrer maintenant",
    "Version {version} is ready for {names}.": "La version {version} est prête pour {names}.",
    "{names} can't update automatically (an older or Mac version, or not the packaged app). Download the new "
    "version there from the Releases page.":
        "{names} ne peut pas se mettre à jour automatiquement (version plus ancienne ou Mac, ou application non "
        "empaquetée). Téléchargez-y la nouvelle version depuis la page Releases.",
    "Version {version} is installed on this computer. Restart the app to start using it.":
        "La version {version} est installée sur cet ordinateur. Redémarrez l’application pour l’utiliser.",
    "Update installed. The app restarts as soon as the running transfers finish.":
        "Mise à jour installée. L’application redémarre dès que les transferts en cours sont terminés.",
    "Update available": "Mise à jour disponible",
    "<b>{name}</b> ({ip}) wants to update {app} on this computer from version {old} to <b>{new}</b>.":
        "<b>{name}</b> ({ip}) veut mettre à jour {app} sur cet ordinateur de la version {old} à la version "
        "<b>{new}</b>.",
    "The update is signed by your computer and checked before it's installed. The app restarts by itself "
    "afterwards, once any running transfers have finished.":
        "La mise à jour est signée par votre ordinateur et vérifiée avant d’être installée. L’application redémarre "
        "ensuite d’elle-même, une fois les transferts en cours terminés.",
    "Update now": "Mettre à jour",
    "Not now": "Plus tard",
    "Answers “Not now” automatically in {seconds} s": "Réponse automatique « Plus tard » dans {seconds} s",
    "{n} transfer still in progress. Stop and restart?": (
        "{n} transfert encore en cours. Arrêter et redémarrer ?",
        "{n} transferts encore en cours. Arrêter et redémarrer ?"),
    "{n} transfer still in progress. Stop and quit?": (
        "{n} transfert encore en cours. Arrêter et quitter ?",
        "{n} transferts encore en cours. Arrêter et quitter ?"),
    "The app couldn't restart by itself. Please open it again.":
        "L’application n’a pas pu redémarrer d’elle-même. Veuillez la rouvrir.",

    # Messages from the transfer engine
    "Connecting": "Connexion",
    "Preparing files": "Préparation des fichiers",
    "Waiting for {name} to accept": "En attente de l’accord de {name}",
    "Waiting for you to accept": "En attente de votre accord",
    "Waiting for the other computer to finish saving": "En attente de la fin de l’enregistrement sur l’autre ordinateur",
    "Saved to {folder}": "Enregistré dans {folder}",
    "Saved to {folder} ({n} file could not be read on the other computer)": (
        "Enregistré dans {folder} ({n} fichier n’a pas pu être lu sur l’autre ordinateur)",
        "Enregistré dans {folder} ({n} fichiers n’ont pas pu être lus sur l’autre ordinateur)"),
    "Delivered to {name}": "Livré à {name}",
    "Delivered to {name} ({n} file could not be read and was skipped)": (
        "Livré à {name} ({n} fichier illisible a été ignoré)",
        "Livré à {name} ({n} fichiers illisibles ont été ignorés)"),
    "Nothing to send - the selected files could not be found.":
        "Rien à envoyer : les fichiers sélectionnés sont introuvables.",
    "Could not connect to {name}. Make sure the app is open there and that its firewall allows it.":
        "Impossible de se connecter à {name}. Vérifiez que l’application y est ouverte et que le pare-feu "
        "l’autorise.",
    "Could not connect. Is the app open on the other computer?":
        "Connexion impossible. L’application est-elle ouverte sur l’autre ordinateur ?",
    "The other computer stopped responding.": "L’autre ordinateur ne répond plus.",
    "The connection to the other computer was lost.": "La connexion avec l’autre ordinateur a été perdue.",
    "The other computer sent unexpected data ({detail}). Are both apps the same version?":
        "L’autre ordinateur a envoyé des données inattendues ({detail}). Les deux applications ont-elles la même "
        "version ?",
    "{name} was damaged in transit (checksum mismatch)":
        "{name} a été endommagé pendant le transfert (somme de contrôle incorrecte)",
    "The other computer stopped the transfer.": "L’autre ordinateur a arrêté le transfert.",
    "The other computer cancelled the transfer.": "L’autre ordinateur a annulé le transfert.",
    "The sender cancelled the transfer.": "L’expéditeur a annulé le transfert.",
    "The sender cancelled before you answered.": "L’expéditeur a annulé avant votre réponse.",
    "You cancelled the transfer.": "Vous avez annulé le transfert.",
    "You declined these files.": "Vous avez refusé ces fichiers.",
    "Not answered in time.": "Pas de réponse à temps.",
    "The other computer declined.": "L’autre ordinateur a refusé.",
    "The other computer declined the files.": "L’autre ordinateur a refusé les fichiers.",
    "Nobody answered on the other computer.": "Personne n’a répondu sur l’autre ordinateur.",
    "The other computer could not save the files: {error}":
        "L’autre ordinateur n’a pas pu enregistrer les fichiers : {error}",
    "The other computer refused the file list (invalid names).":
        "L’autre ordinateur a refusé la liste des fichiers (noms non valides).",
    "The two apps are different versions. Please update both.":
        "Les deux applications ont des versions différentes. Mettez-les à jour toutes les deux.",

    # Messages from the update engine
    "Waiting for {name} to accept the update": "En attente de l’accord de {name} pour la mise à jour",
    "Waiting for you to accept the update": "En attente de votre accord pour la mise à jour",
    "{name} is checking and installing the update": "{name} vérifie et installe la mise à jour",
    "{name} now has version {version} and is restarting.": "{name} a maintenant la version {version} et redémarre.",
    "Checking that the new version starts": "Vérification du démarrage de la nouvelle version",
    "Version {version} installed. Restarting…": "Version {version} installée. Redémarrage…",
    "You chose not to update now.": "Vous avez choisi « Plus tard ».",
    "The other computer chose not to update now.": "L’autre ordinateur a choisi « Plus tard ».",
    "You cancelled the update.": "Vous avez annulé la mise à jour.",
    "The other computer cancelled the update.": "L’autre ordinateur a annulé la mise à jour.",
    "The sender cancelled the update.": "L’expéditeur a annulé la mise à jour.",
    "The update failed on the other computer: {error}": "La mise à jour a échoué sur l’autre ordinateur : {error}",
    "The update isn't signed by your computer, so it was refused.":
        "La mise à jour n’est pas signée par votre ordinateur, elle a donc été refusée.",
    "The update information is damaged.": "Les informations de mise à jour sont endommagées.",
    "Updates aren't set up in this copy of the app.":
        "Les mises à jour ne sont pas configurées dans cette copie de l’application.",
    "The update has no version for {system}.": "La mise à jour ne contient pas de version pour {system}.",
    "That computer already has version {version} or newer.":
        "Cet ordinateur a déjà la version {version} ou une plus récente.",
    "That copy of the app can't update itself (it isn't the packaged app, or its folder is read-only). Copy the "
    "new version there by hand.":
        "Cette copie de l’application ne peut pas se mettre à jour elle-même (ce n’est pas l’application "
        "empaquetée, ou son dossier est en lecture seule). Copiez-y la nouvelle version à la main.",
    "The downloaded update doesn't match its signature, so it was discarded.":
        "La mise à jour téléchargée ne correspond pas à sa signature, elle a donc été supprimée.",
    "The new version didn't start correctly on this computer, so the current version was kept.":
        "La nouvelle version n’a pas démarré correctement sur cet ordinateur, la version actuelle a donc été "
        "conservée.",

    # Units (octets), durations, months
    "B": "o", "KB": "Ko", "MB": "Mo", "GB": "Go", "TB": "To",
    "{s} s": "{s} s",
    "{m} min {s:02d} s": "{m} min {s:02d} s",
    "{h} h {m:02d} min": "{h} h {m:02d} min",
    "Jan": "janv.", "Feb": "févr.", "Mar": "mars", "Apr": "avr.", "May": "mai", "Jun": "juin",
    "Jul": "juil.", "Aug": "août", "Sep": "sept.", "Oct": "oct.", "Nov": "nov.", "Dec": "déc.",
}
