"""Deutsch (Anrede: du)."""

MESSAGES = {
    # Window
    "Settings": "Einstellungen",
    "Light or dark appearance": "Helles oder dunkles Aussehen",
    "Light": "Hell",
    "Dark": "Dunkel",
    "Auto": "Auto",
    "Same as system": "Wie das System",
    "This computer: <b>{name}</b>": "Dieser Computer: <b>{name}</b>",
    "All addresses: {addresses}": "Alle Adressen: {addresses}",
    "no network connection": "keine Netzwerkverbindung",
    "Choose the computer to send to": "Computer auswählen, an den gesendet wird",
    "Add computer by IP address…": "Computer per IP-Adresse hinzufügen…",
    "Choose files and folders": "Dateien und Ordner auswählen",
    "Drag files or folders here\n\nor use the buttons below":
        "Dateien oder Ordner hierher ziehen\n\noder die Schaltflächen unten verwenden",
    "Add files…": "Dateien hinzufügen…",
    "Add folder…": "Ordner hinzufügen…",
    "Remove": "Entfernen",
    "Clear": "Leeren",
    "Send": "Senden",
    "Send {n} item to {name}": ("{n} Element an {name} senden", "{n} Elemente an {name} senden"),
    "Choose a computer and add some files first.": "Wähle zuerst einen Computer und füge Dateien hinzu.",
    "Transfers": "Übertragungen",
    "Nothing sent or received yet.": "Noch nichts gesendet oder empfangen.",
    "Received files are saved in:  {folder}": "Empfangene Dateien werden gespeichert in:  {folder}",
    "Change…": "Ändern…",
    "Open": "Öffnen",
    "folder": "Ordner",
    "Choose files to send": "Zu sendende Dateien auswählen",
    "Choose a folder to send": "Zu sendenden Ordner auswählen",
    "Save received files in": "Ordner für empfangene Dateien",
    "This computer cannot receive files right now:\n{error}\n\nSending still works.":
        "Dieser Computer kann gerade keine Dateien empfangen:\n{error}\n\nSenden funktioniert weiterhin.",

    # Computers list
    "Looking for other computers…": "Suche nach anderen Computern…",
    "No other computers found yet.\n\nOpen {app} on the other computer and make sure both are on the same Wi-Fi."
    "\n\nIf a firewall question pops up, click Allow.":
        "Noch keine anderen Computer gefunden.\n\nÖffne {app} auf dem anderen Computer und achte darauf, dass beide "
        "im selben WLAN sind.\n\nWenn eine Firewall-Frage erscheint, klicke auf Zulassen.",
    "Use “Add computer by IP address…” instead.": "Verwende stattdessen „Computer per IP-Adresse hinzufügen…“.",
    "Automatic discovery is unavailable (UDP port {port}: {error}).":
        "Die automatische Suche ist nicht verfügbar (UDP-Port {port}: {error}).",
    "Version {version}": "Version {version}",
    "Older version": "Ältere Version",
    "update ready": "Update bereit",
    "Send files to {name}": "Dateien an {name} senden",
    "Update to version {version}": "Auf Version {version} aktualisieren",
    "Forget this computer": "Diesen Computer vergessen",
    "Add computer by IP address": "Computer per IP-Adresse hinzufügen",
    "Type the IP address shown at the top of {app} on the other computer\n(for example 192.168.1.42):":
        "Gib die IP-Adresse ein, die oben in {app} auf dem anderen Computer angezeigt wird\n"
        "(zum Beispiel 192.168.1.42):",
    "“{text}” is not a valid IP address.": "„{text}“ ist keine gültige IP-Adresse.",
    "Could not reach {address}.\n\nCheck that {app} is open on that computer, that both computers are on the "
    "same network, and that its firewall allows the app.":
        "{address} ist nicht erreichbar.\n\nPrüfe, ob {app} auf diesem Computer geöffnet ist, ob beide Computer "
        "im selben Netzwerk sind und ob die Firewall die App zulässt.",

    # Transfer rows
    "Cancel": "Abbrechen",
    "Open folder": "Ordner öffnen",
    "Remove from list": "Aus der Liste entfernen",
    "Sending “{item}” to {name}": "Sende „{item}“ an {name}",
    "Sent “{item}” to {name}": "„{item}“ an {name} gesendet",
    "Sending {n} item to {name}": ("Sende {n} Element an {name}", "Sende {n} Elemente an {name}"),
    "Sent {n} item to {name}": ("{n} Element an {name} gesendet", "{n} Elemente an {name} gesendet"),
    "Receiving “{item}” from {name}": "Empfange „{item}“ von {name}",
    "Received “{item}” from {name}": "„{item}“ von {name} empfangen",
    "Receiving {n} item from {name}": ("Empfange {n} Element von {name}", "Empfange {n} Elemente von {name}"),
    "Received {n} item from {name}": ("{n} Element von {name} empfangen", "{n} Elemente von {name} empfangen"),
    "Updating {name} to version {version}": "Aktualisiere {name} auf Version {version}",
    "Updated {name} to version {version}": "{name} auf Version {version} aktualisiert",
    "Receiving version {version} from {name}": "Empfange Version {version} von {name}",
    "Installed version {version} from {name}": "Version {version} von {name} installiert",
    "Starting": "Starte",
    "{done} of {total}": "{done} von {total}",
    "about {time} left": "noch etwa {time}",
    "file {current} of {total}": "Datei {current} von {total}",
    "{size} in {time}": "{size} in {time}",
    "Done": "Fertig",
    "Failed": "Fehlgeschlagen",
    "Cancelled": "Abgebrochen",
    "Declined": "Abgelehnt",
    "{n} file": ("{n} Datei", "{n} Dateien"),

    # Incoming files
    "Incoming files": "Eingehende Dateien",
    "<b>{name}</b> ({os} · {ip}) wants to send you {files} ({size}).":
        "<b>{name}</b> ({os} · {ip}) möchte dir {files} senden ({size}).",
    "{name}   —   folder, {files}, {size}": "{name}   —   Ordner, {files}, {size}",
    "They will be saved in a new numbered folder inside: {folder}":
        "Sie werden in einem neuen, nummerierten Ordner gespeichert in: {folder}",
    "⚠ Not enough free space: only {size} available.": "⚠ Nicht genug freier Speicherplatz: nur {size} verfügbar.",
    "Accept": "Annehmen",
    "Decline": "Ablehnen",
    "Declines automatically in {seconds} s": "Wird in {seconds} s automatisch abgelehnt",

    # Settings
    "Name of this computer:": "Name dieses Computers:",
    "Save received files in:": "Empfangene Dateien speichern in:",
    "Browse…": "Durchsuchen…",
    "Ask me before accepting incoming files (recommended)": "Vor dem Annehmen eingehender Dateien fragen (empfohlen)",
    "Appearance:": "Aussehen:",
    "Language:": "Sprache:",
    "Automatic (system language)": "Automatisch (Systemsprache)",
    "IP address: {ip}": "IP-Adresse: {ip}",
    "not connected": "nicht verbunden",
    "Port: {port}": "Port: {port}",
    "not listening": "nicht empfangsbereit",
    "The new language is used after {app} restarts. Restart now?":
        "Die neue Sprache wird nach einem Neustart von {app} verwendet. Jetzt neu starten?",

    # Updates
    "Update": "Aktualisieren",
    "Update {name}": "{name} aktualisieren",
    "Update all ({n})": "Alle aktualisieren ({n})",
    "Restart now": "Jetzt neu starten",
    "Version {version} is ready for {names}.": "Version {version} ist bereit für {names}.",
    "{names} can't update automatically (an older or Mac version, or not the packaged app). Download the new "
    "version there from the Releases page.":
        "{names} kann nicht automatisch aktualisiert werden (ältere oder Mac-Version oder nicht die gepackte App). "
        "Lade dort die neue Version von der Releases-Seite herunter.",
    "Version {version} is installed on this computer. Restart the app to start using it.":
        "Version {version} ist auf diesem Computer installiert. Starte die App neu, um sie zu verwenden.",
    "Update installed. The app restarts as soon as the running transfers finish.":
        "Update installiert. Die App startet neu, sobald die laufenden Übertragungen abgeschlossen sind.",
    "Update available": "Update verfügbar",
    "<b>{name}</b> ({ip}) wants to update {app} on this computer from version {old} to <b>{new}</b>.":
        "<b>{name}</b> ({ip}) möchte {app} auf diesem Computer von Version {old} auf <b>{new}</b> aktualisieren.",
    "The update is signed by your computer and checked before it's installed. The app restarts by itself "
    "afterwards, once any running transfers have finished.":
        "Das Update ist von deinem Computer signiert und wird vor der Installation geprüft. Danach startet die App "
        "von selbst neu, sobald laufende Übertragungen abgeschlossen sind.",
    "Update now": "Jetzt aktualisieren",
    "Not now": "Nicht jetzt",
    "Answers “Not now” automatically in {seconds} s": "Antwortet in {seconds} s automatisch „Nicht jetzt“",
    "{n} transfer still in progress. Stop and restart?": (
        "{n} Übertragung läuft noch. Abbrechen und neu starten?",
        "{n} Übertragungen laufen noch. Abbrechen und neu starten?"),
    "{n} transfer still in progress. Stop and quit?": (
        "{n} Übertragung läuft noch. Abbrechen und beenden?",
        "{n} Übertragungen laufen noch. Abbrechen und beenden?"),
    "The app couldn't restart by itself. Please open it again.":
        "Die App konnte nicht von selbst neu starten. Bitte öffne sie erneut.",

    # Messages from the transfer engine
    "Connecting": "Verbinde",
    "Preparing files": "Bereite Dateien vor",
    "Waiting for {name} to accept": "Warte auf Zustimmung von {name}",
    "Waiting for you to accept": "Wartet auf deine Zustimmung",
    "Waiting for the other computer to finish saving": "Warte, bis der andere Computer fertig gespeichert hat",
    "Saved to {folder}": "Gespeichert in {folder}",
    "Saved to {folder} ({n} file could not be read on the other computer)": (
        "Gespeichert in {folder} ({n} Datei konnte auf dem anderen Computer nicht gelesen werden)",
        "Gespeichert in {folder} ({n} Dateien konnten auf dem anderen Computer nicht gelesen werden)"),
    "Delivered to {name}": "An {name} zugestellt",
    "Delivered to {name} ({n} file could not be read and was skipped)": (
        "An {name} zugestellt ({n} Datei konnte nicht gelesen werden und wurde übersprungen)",
        "An {name} zugestellt ({n} Dateien konnten nicht gelesen werden und wurden übersprungen)"),
    "Nothing to send - the selected files could not be found.":
        "Nichts zu senden – die ausgewählten Dateien wurden nicht gefunden.",
    "Could not connect to {name}. Make sure the app is open there and that its firewall allows it.":
        "Keine Verbindung zu {name}. Stelle sicher, dass die App dort geöffnet ist und die Firewall sie zulässt.",
    "Could not connect. Is the app open on the other computer?":
        "Verbindung nicht möglich. Ist die App auf dem anderen Computer geöffnet?",
    "The other computer stopped responding.": "Der andere Computer antwortet nicht mehr.",
    "The connection to the other computer was lost.": "Die Verbindung zum anderen Computer wurde unterbrochen.",
    "The other computer sent unexpected data ({detail}). Are both apps the same version?":
        "Der andere Computer hat unerwartete Daten gesendet ({detail}). Haben beide Apps dieselbe Version?",
    "{name} was damaged in transit (checksum mismatch)":
        "{name} wurde bei der Übertragung beschädigt (Prüfsumme stimmt nicht)",
    "The other computer stopped the transfer.": "Der andere Computer hat die Übertragung beendet.",
    "The other computer cancelled the transfer.": "Der andere Computer hat die Übertragung abgebrochen.",
    "The sender cancelled the transfer.": "Der Absender hat die Übertragung abgebrochen.",
    "The sender cancelled before you answered.": "Der Absender hat abgebrochen, bevor du geantwortet hast.",
    "You cancelled the transfer.": "Du hast die Übertragung abgebrochen.",
    "You declined these files.": "Du hast diese Dateien abgelehnt.",
    "Not answered in time.": "Nicht rechtzeitig beantwortet.",
    "The other computer declined.": "Der andere Computer hat abgelehnt.",
    "The other computer declined the files.": "Der andere Computer hat die Dateien abgelehnt.",
    "Nobody answered on the other computer.": "Auf dem anderen Computer hat niemand geantwortet.",
    "The other computer could not save the files: {error}":
        "Der andere Computer konnte die Dateien nicht speichern: {error}",
    "The other computer refused the file list (invalid names).":
        "Der andere Computer hat die Dateiliste abgelehnt (ungültige Namen).",
    "The two apps are different versions. Please update both.":
        "Die beiden Apps haben unterschiedliche Versionen. Bitte aktualisiere beide.",

    # Messages from the update engine
    "Waiting for {name} to accept the update": "Warte, bis {name} dem Update zustimmt",
    "Waiting for you to accept the update": "Wartet auf deine Zustimmung zum Update",
    "{name} is checking and installing the update": "{name} prüft und installiert das Update",
    "{name} now has version {version} and is restarting.": "{name} hat jetzt Version {version} und startet neu.",
    "Checking that the new version starts": "Prüfe, ob die neue Version startet",
    "Version {version} installed. Restarting…": "Version {version} installiert. Starte neu…",
    "You chose not to update now.": "Du hast „Nicht jetzt“ gewählt.",
    "The other computer chose not to update now.": "Auf dem anderen Computer wurde „Nicht jetzt“ gewählt.",
    "You cancelled the update.": "Du hast das Update abgebrochen.",
    "The other computer cancelled the update.": "Der andere Computer hat das Update abgebrochen.",
    "The sender cancelled the update.": "Der Absender hat das Update abgebrochen.",
    "The update failed on the other computer: {error}":
        "Das Update ist auf dem anderen Computer fehlgeschlagen: {error}",
    "The update isn't signed by your computer, so it was refused.":
        "Das Update ist nicht von deinem Computer signiert und wurde daher abgelehnt.",
    "The update information is damaged.": "Die Update-Informationen sind beschädigt.",
    "Updates aren't set up in this copy of the app.": "Updates sind in dieser Kopie der App nicht eingerichtet.",
    "The update has no version for {system}.": "Das Update enthält keine Version für {system}.",
    "That computer already has version {version} or newer.":
        "Dieser Computer hat bereits Version {version} oder neuer.",
    "That copy of the app can't update itself (it isn't the packaged app, or its folder is read-only). Copy the "
    "new version there by hand.":
        "Diese Kopie der App kann sich nicht selbst aktualisieren (sie ist nicht die gepackte App, oder ihr Ordner "
        "ist schreibgeschützt). Kopiere die neue Version von Hand dorthin.",
    "The downloaded update doesn't match its signature, so it was discarded.":
        "Das heruntergeladene Update passt nicht zu seiner Signatur und wurde verworfen.",
    "The new version didn't start correctly on this computer, so the current version was kept.":
        "Die neue Version ist auf diesem Computer nicht richtig gestartet, daher wurde die aktuelle Version "
        "behalten.",

    # Units, durations, months
    "B": "B", "KB": "KB", "MB": "MB", "GB": "GB", "TB": "TB",
    "{s} s": "{s} s",
    "{m} min {s:02d} s": "{m} Min. {s:02d} s",
    "{h} h {m:02d} min": "{h} Std. {m:02d} Min.",
    "Jan": "Jan", "Feb": "Feb", "Mar": "März", "Apr": "Apr", "May": "Mai", "Jun": "Juni",
    "Jul": "Juli", "Aug": "Aug", "Sep": "Sept", "Oct": "Okt", "Nov": "Nov", "Dec": "Dez",
    # Resuming interrupted transfers
    "Resume": "Fortsetzen",
    "Discard": "Verwerfen",
    "Interrupted": "Unterbrochen",
    "Resuming": "Setze fort",
    "It continues by itself when {name} is back online, or click Resume.":
        "Sie geht von selbst weiter, sobald {name} wieder online ist, oder klicke auf Fortsetzen.",
    "It continues when {name} sends the rest.": "Sie geht weiter, sobald {name} den Rest sendet.",
    "Checking the part that was already sent": "Prüfe den bereits gesendeten Teil",
    "Checking the part that already arrived": "Prüfe den bereits angekommenen Teil",
    "The transfer was interrupted.": "Die Übertragung wurde unterbrochen.",
    "The other computer closed the app.": "Auf dem anderen Computer wurde die App geschlossen.",
    "This app was closed during the transfer.": "Die App wurde während der Übertragung geschlossen.",
    "The other computer stopped this transfer for good.": "Der andere Computer hat diese Übertragung endgültig beendet.",
    "The sender stopped this transfer for good.": "Der Absender hat diese Übertragung endgültig beendet.",
    "The other computer could not read the files: {error}": "Der andere Computer konnte die Dateien nicht lesen: {error}",
    "Stop this transfer for good? The files that already arrived on {name} stay there.":
        "Diese Übertragung endgültig beenden? Die Dateien, die schon auf {name} angekommen sind, bleiben dort.",
    "Stop this transfer for good? The files that already arrived stay in the folder; the unfinished one is deleted.":
        "Diese Übertragung endgültig beenden? Die Dateien, die schon angekommen sind, bleiben im Ordner; die "
        "unvollständige wird gelöscht.",
    "{n} transfer still in progress. Restart anyway?\n\nIt continues where it stopped after the restart.": (
        "{n} Übertragung läuft noch. Trotzdem neu starten?\n\nSie wird nach dem Neustart dort fortgesetzt, "
        "wo sie aufgehört hat.",
        "{n} Übertragungen laufen noch. Trotzdem neu starten?\n\nSie werden nach dem Neustart dort "
        "fortgesetzt, wo sie aufgehört haben."),
    "{n} transfer still in progress. Quit anyway?\n\nIt continues where it stopped the next time both computers have the app open.": (
        "{n} Übertragung läuft noch. Trotzdem beenden?\n\nSie wird dort fortgesetzt, wo sie aufgehört hat, "
        "sobald die App auf beiden Computern wieder geöffnet ist.",
        "{n} Übertragungen laufen noch. Trotzdem beenden?\n\nSie werden dort fortgesetzt, wo sie aufgehört "
        "haben, sobald die App auf beiden Computern wieder geöffnet ist."),
}
