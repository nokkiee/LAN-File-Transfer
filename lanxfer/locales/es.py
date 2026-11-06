"""Español (tuteo)."""

MESSAGES = {
    # Window
    "Settings": "Ajustes",
    "Light or dark appearance": "Apariencia clara u oscura",
    "Light": "Claro",
    "Dark": "Oscuro",
    "Auto": "Auto",
    "Same as system": "Igual que el sistema",
    "This computer: <b>{name}</b>": "Este equipo: <b>{name}</b>",
    "All addresses: {addresses}": "Todas las direcciones: {addresses}",
    "no network connection": "sin conexión de red",
    "Choose the computer to send to": "Elige el equipo al que enviar",
    "Add computer by IP address…": "Añadir equipo por dirección IP…",
    "Choose files and folders": "Elige archivos y carpetas",
    "Drag files or folders here\n\nor use the buttons below":
        "Arrastra archivos o carpetas aquí\n\no usa los botones de abajo",
    "Add files…": "Añadir archivos…",
    "Add folder…": "Añadir carpeta…",
    "Remove": "Quitar",
    "Clear": "Vaciar",
    "Send": "Enviar",
    "Send {n} item to {name}": ("Enviar {n} elemento a {name}", "Enviar {n} elementos a {name}"),
    "Choose a computer and add some files first.": "Primero elige un equipo y añade algunos archivos.",
    "Transfers": "Transferencias",
    "Nothing sent or received yet.": "Todavía no se ha enviado ni recibido nada.",
    "Received files are saved in:  {folder}": "Los archivos recibidos se guardan en:  {folder}",
    "Change…": "Cambiar…",
    "Open": "Abrir",
    "folder": "carpeta",
    "Choose files to send": "Elige los archivos que quieres enviar",
    "Choose a folder to send": "Elige la carpeta que quieres enviar",
    "Save received files in": "Guardar los archivos recibidos en",
    "This computer cannot receive files right now:\n{error}\n\nSending still works.":
        "Este equipo no puede recibir archivos ahora mismo:\n{error}\n\nEl envío sigue funcionando.",

    # Computers list
    "Looking for other computers…": "Buscando otros equipos…",
    "No other computers found yet.\n\nOpen {app} on the other computer and make sure both are on the same Wi-Fi."
    "\n\nIf a firewall question pops up, click Allow.":
        "Todavía no se han encontrado otros equipos.\n\nAbre {app} en el otro equipo y comprueba que ambos estén en "
        "la misma red Wi-Fi.\n\nSi el cortafuegos pregunta algo, haz clic en Permitir.",
    "Use “Add computer by IP address…” instead.": "Usa «Añadir equipo por dirección IP…» en su lugar.",
    "Automatic discovery is unavailable (UDP port {port}: {error}).":
        "La búsqueda automática no está disponible (puerto UDP {port}: {error}).",
    "Version {version}": "Versión {version}",
    "Older version": "Versión anterior",
    "update ready": "actualización lista",
    "Send files to {name}": "Enviar archivos a {name}",
    "Update to version {version}": "Actualizar a la versión {version}",
    "Forget this computer": "Olvidar este equipo",
    "Add computer by IP address": "Añadir equipo por dirección IP",
    "Type the IP address shown at the top of {app} on the other computer\n(for example 192.168.1.42):":
        "Escribe la dirección IP que aparece arriba en {app} en el otro equipo\n(por ejemplo 192.168.1.42):",
    "“{text}” is not a valid IP address.": "«{text}» no es una dirección IP válida.",
    "Could not reach {address}.\n\nCheck that {app} is open on that computer, that both computers are on the "
    "same network, and that its firewall allows the app.":
        "No se pudo conectar con {address}.\n\nComprueba que {app} esté abierto en ese equipo, que ambos equipos "
        "estén en la misma red y que el cortafuegos permita la aplicación.",

    # Transfer rows
    "Cancel": "Cancelar",
    "Open folder": "Abrir carpeta",
    "Remove from list": "Quitar de la lista",
    "Sending “{item}” to {name}": "Enviando «{item}» a {name}",
    "Sent “{item}” to {name}": "«{item}» enviado a {name}",
    "Sending {n} item to {name}": ("Enviando {n} elemento a {name}", "Enviando {n} elementos a {name}"),
    "Sent {n} item to {name}": ("{n} elemento enviado a {name}", "{n} elementos enviados a {name}"),
    "Receiving “{item}” from {name}": "Recibiendo «{item}» de {name}",
    "Received “{item}” from {name}": "«{item}» recibido de {name}",
    "Receiving {n} item from {name}": ("Recibiendo {n} elemento de {name}", "Recibiendo {n} elementos de {name}"),
    "Received {n} item from {name}": ("{n} elemento recibido de {name}", "{n} elementos recibidos de {name}"),
    "Updating {name} to version {version}": "Actualizando {name} a la versión {version}",
    "Updated {name} to version {version}": "{name} actualizado a la versión {version}",
    "Receiving version {version} from {name}": "Recibiendo la versión {version} de {name}",
    "Installed version {version} from {name}": "Versión {version} instalada desde {name}",
    "Starting": "Iniciando",
    "{done} of {total}": "{done} de {total}",
    "about {time} left": "quedan unos {time}",
    "file {current} of {total}": "archivo {current} de {total}",
    "{size} in {time}": "{size} en {time}",
    "Done": "Hecho",
    "Failed": "Error",
    "Cancelled": "Cancelado",
    "Declined": "Rechazado",
    "{n} file": ("{n} archivo", "{n} archivos"),

    # Incoming files
    "Incoming files": "Archivos entrantes",
    "<b>{name}</b> ({os} · {ip}) wants to send you {files} ({size}).":
        "<b>{name}</b> ({os} · {ip}) quiere enviarte {files} ({size}).",
    "{name}   —   folder, {files}, {size}": "{name}   —   carpeta, {files}, {size}",
    "They will be saved in a new numbered folder inside: {folder}":
        "Se guardarán en una nueva carpeta numerada dentro de: {folder}",
    "⚠ Not enough free space: only {size} available.":
        "⚠ No hay suficiente espacio libre: solo hay {size} disponibles.",
    "Accept": "Aceptar",
    "Decline": "Rechazar",
    "Declines automatically in {seconds} s": "Se rechaza automáticamente en {seconds} s",

    # Settings
    "Name of this computer:": "Nombre de este equipo:",
    "Save received files in:": "Guardar los archivos recibidos en:",
    "Browse…": "Examinar…",
    "Ask me before accepting incoming files (recommended)":
        "Preguntarme antes de aceptar archivos entrantes (recomendado)",
    "Appearance:": "Apariencia:",
    "Language:": "Idioma:",
    "Automatic (system language)": "Automático (idioma del sistema)",
    "IP address: {ip}": "Dirección IP: {ip}",
    "not connected": "sin conexión",
    "Port: {port}": "Puerto: {port}",
    "not listening": "sin escuchar",
    "The new language is used after {app} restarts. Restart now?":
        "El nuevo idioma se usará cuando {app} se reinicie. ¿Reiniciar ahora?",

    # Updates
    "Update": "Actualizar",
    "Update {name}": "Actualizar {name}",
    "Update all ({n})": "Actualizar todos ({n})",
    "Restart now": "Reiniciar ahora",
    "Version {version} is ready for {names}.": "La versión {version} está lista para {names}.",
    "{names} can't update automatically (an older or Mac version, or not the packaged app). Download the new "
    "version there from the Releases page.":
        "{names} no se puede actualizar automáticamente (versión anterior o de Mac, o no es la aplicación "
        "empaquetada). Descarga allí la nueva versión desde la página Releases.",
    "Version {version} is installed on this computer. Restart the app to start using it.":
        "La versión {version} está instalada en este equipo. Reinicia la aplicación para empezar a usarla.",
    "Update installed. The app restarts as soon as the running transfers finish.":
        "Actualización instalada. La aplicación se reiniciará en cuanto terminen las transferencias en curso.",
    "Update available": "Actualización disponible",
    "<b>{name}</b> ({ip}) wants to update {app} on this computer from version {old} to <b>{new}</b>.":
        "<b>{name}</b> ({ip}) quiere actualizar {app} en este equipo de la versión {old} a la <b>{new}</b>.",
    "The update is signed by your computer and checked before it's installed. The app restarts by itself "
    "afterwards, once any running transfers have finished.":
        "La actualización está firmada por tu equipo y se comprueba antes de instalarla. Después, la aplicación "
        "se reinicia sola cuando terminen las transferencias en curso.",
    "Update now": "Actualizar ahora",
    "Not now": "Ahora no",
    "Answers “Not now” automatically in {seconds} s": "Responde «Ahora no» automáticamente en {seconds} s",
    "{n} transfer still in progress. Stop and restart?": (
        "{n} transferencia sigue en curso. ¿Detener y reiniciar?",
        "{n} transferencias siguen en curso. ¿Detener y reiniciar?"),
    "{n} transfer still in progress. Stop and quit?": (
        "{n} transferencia sigue en curso. ¿Detener y salir?",
        "{n} transferencias siguen en curso. ¿Detener y salir?"),
    "The app couldn't restart by itself. Please open it again.":
        "La aplicación no pudo reiniciarse sola. Vuelve a abrirla.",

    # Messages from the transfer engine
    "Connecting": "Conectando",
    "Preparing files": "Preparando archivos",
    "Waiting for {name} to accept": "Esperando a que {name} acepte",
    "Waiting for you to accept": "Esperando tu aceptación",
    "Waiting for the other computer to finish saving": "Esperando a que el otro equipo termine de guardar",
    "Saved to {folder}": "Guardado en {folder}",
    "Saved to {folder} ({n} file could not be read on the other computer)": (
        "Guardado en {folder} ({n} archivo no se pudo leer en el otro equipo)",
        "Guardado en {folder} ({n} archivos no se pudieron leer en el otro equipo)"),
    "Delivered to {name}": "Entregado a {name}",
    "Delivered to {name} ({n} file could not be read and was skipped)": (
        "Entregado a {name} ({n} archivo no se pudo leer y se omitió)",
        "Entregado a {name} ({n} archivos no se pudieron leer y se omitieron)"),
    "Nothing to send - the selected files could not be found.":
        "No hay nada que enviar: no se encontraron los archivos seleccionados.",
    "Could not connect to {name}. Make sure the app is open there and that its firewall allows it.":
        "No se pudo conectar con {name}. Comprueba que la aplicación esté abierta allí y que el cortafuegos la "
        "permita.",
    "Could not connect. Is the app open on the other computer?":
        "No se pudo conectar. ¿Está abierta la aplicación en el otro equipo?",
    "The other computer stopped responding.": "El otro equipo dejó de responder.",
    "The connection to the other computer was lost.": "Se perdió la conexión con el otro equipo.",
    "The other computer sent unexpected data ({detail}). Are both apps the same version?":
        "El otro equipo envió datos inesperados ({detail}). ¿Tienen ambas aplicaciones la misma versión?",
    "{name} was damaged in transit (checksum mismatch)":
        "{name} se dañó durante la transferencia (la suma de comprobación no coincide)",
    "The other computer stopped the transfer.": "El otro equipo detuvo la transferencia.",
    "The other computer cancelled the transfer.": "El otro equipo canceló la transferencia.",
    "The sender cancelled the transfer.": "El remitente canceló la transferencia.",
    "The sender cancelled before you answered.": "El remitente canceló antes de que respondieras.",
    "You cancelled the transfer.": "Cancelaste la transferencia.",
    "You declined these files.": "Rechazaste estos archivos.",
    "Not answered in time.": "No se respondió a tiempo.",
    "The other computer declined.": "El otro equipo lo rechazó.",
    "The other computer declined the files.": "El otro equipo rechazó los archivos.",
    "Nobody answered on the other computer.": "Nadie respondió en el otro equipo.",
    "The other computer could not save the files: {error}": "El otro equipo no pudo guardar los archivos: {error}",
    "The other computer refused the file list (invalid names).":
        "El otro equipo rechazó la lista de archivos (nombres no válidos).",
    "The two apps are different versions. Please update both.":
        "Las dos aplicaciones tienen versiones distintas. Actualiza ambas.",

    # Messages from the update engine
    "Waiting for {name} to accept the update": "Esperando a que {name} acepte la actualización",
    "Waiting for you to accept the update": "Esperando que aceptes la actualización",
    "{name} is checking and installing the update": "{name} está comprobando e instalando la actualización",
    "{name} now has version {version} and is restarting.":
        "{name} ya tiene la versión {version} y se está reiniciando.",
    "Checking that the new version starts": "Comprobando que la nueva versión se inicia",
    "Version {version} installed. Restarting…": "Versión {version} instalada. Reiniciando…",
    "You chose not to update now.": "Elegiste «Ahora no».",
    "The other computer chose not to update now.": "En el otro equipo se eligió «Ahora no».",
    "You cancelled the update.": "Cancelaste la actualización.",
    "The other computer cancelled the update.": "El otro equipo canceló la actualización.",
    "The sender cancelled the update.": "El remitente canceló la actualización.",
    "The update failed on the other computer: {error}": "La actualización falló en el otro equipo: {error}",
    "The update isn't signed by your computer, so it was refused.":
        "La actualización no está firmada por tu equipo, así que se rechazó.",
    "The update information is damaged.": "La información de la actualización está dañada.",
    "Updates aren't set up in this copy of the app.":
        "Las actualizaciones no están configuradas en esta copia de la aplicación.",
    "The update has no version for {system}.": "La actualización no incluye una versión para {system}.",
    "That computer already has version {version} or newer.":
        "Ese equipo ya tiene la versión {version} o una más reciente.",
    "That copy of the app can't update itself (it isn't the packaged app, or its folder is read-only). Copy the "
    "new version there by hand.":
        "Esa copia de la aplicación no puede actualizarse sola (no es la aplicación empaquetada o su carpeta es de "
        "solo lectura). Copia allí la nueva versión a mano.",
    "The downloaded update doesn't match its signature, so it was discarded.":
        "La actualización descargada no coincide con su firma, así que se descartó.",
    "The new version didn't start correctly on this computer, so the current version was kept.":
        "La nueva versión no se inició correctamente en este equipo, así que se mantuvo la versión actual.",

    # Units, durations, months
    "B": "B", "KB": "KB", "MB": "MB", "GB": "GB", "TB": "TB",
    "{s} s": "{s} s",
    "{m} min {s:02d} s": "{m} min {s:02d} s",
    "{h} h {m:02d} min": "{h} h {m:02d} min",
    "Jan": "ene", "Feb": "feb", "Mar": "mar", "Apr": "abr", "May": "may", "Jun": "jun",
    "Jul": "jul", "Aug": "ago", "Sep": "sept", "Oct": "oct", "Nov": "nov", "Dec": "dic",
}
