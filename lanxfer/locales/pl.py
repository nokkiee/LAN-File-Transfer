"""Polski. Liczba mnoga: (1, 2–4, 5+) – np. 1 plik, 2 pliki, 5 plików."""

MESSAGES = {
    # Window
    "Settings": "Ustawienia",
    "Light or dark appearance": "Jasny lub ciemny wygląd",
    "Light": "Jasny",
    "Dark": "Ciemny",
    "Auto": "Auto",
    "Same as system": "Jak w systemie",
    "This computer: <b>{name}</b>": "Ten komputer: <b>{name}</b>",
    "All addresses: {addresses}": "Wszystkie adresy: {addresses}",
    "no network connection": "brak połączenia z siecią",
    "Choose the computer to send to": "Wybierz komputer, do którego chcesz wysłać",
    "Add computer by IP address…": "Dodaj komputer po adresie IP…",
    "Choose files and folders": "Wybierz pliki i foldery",
    "Drag files or folders here,\npaste copied files or images with {key}\n\nor use the buttons below":
        "Przeciągnij tutaj pliki lub foldery,\nwklej skopiowane pliki lub obrazy skrótem {key}\n\nalbo użyj przycisków poniżej",
    "Paste": "Wklej",
    "Pasted image": "Wklejony obraz",
    "Pasted text": "Wklejony tekst",
    "Could not save what you pasted:\n{error}": "Nie udało się zapisać wklejonej zawartości:\n{error}",
    "There is nothing to paste. Copy some files or an image first.":
        "Nie ma czego wkleić. Najpierw skopiuj pliki lub obraz.",
    "Add files…": "Dodaj pliki…",
    "Add folder…": "Dodaj folder…",
    "Remove": "Usuń",
    "Clear": "Wyczyść",
    "Send": "Wyślij",
    "Send {n} item to {name}": ("Wyślij {n} element do {name}", "Wyślij {n} elementy do {name}",
                                "Wyślij {n} elementów do {name}"),
    "Choose a computer and add some files first.": "Najpierw wybierz komputer i dodaj pliki.",
    "Transfers": "Przesyłania",
    "Nothing sent or received yet.": "Nic jeszcze nie wysłano ani nie odebrano.",
    "Received files are saved in:  {folder}": "Odebrane pliki są zapisywane w:  {folder}",
    "Change…": "Zmień…",
    "Open": "Otwórz",
    "folder": "folder",
    "Choose files to send": "Wybierz pliki do wysłania",
    "Choose a folder to send": "Wybierz folder do wysłania",
    "Save received files in": "Wybierz folder na odebrane pliki",
    "This computer cannot receive files right now:\n{error}\n\nSending still works.":
        "Ten komputer nie może teraz odbierać plików:\n{error}\n\nWysyłanie nadal działa.",

    # Computers list
    "Looking for other computers…": "Szukanie innych komputerów…",
    "No other computers found yet.\n\nOpen {app} on the other computer and make sure both are on the same Wi-Fi."
    "\n\nIf a firewall question pops up, click Allow.":
        "Nie znaleziono jeszcze innych komputerów.\n\nOtwórz {app} na drugim komputerze i upewnij się, że oba są "
        "w tej samej sieci Wi-Fi.\n\nJeśli zapora zapyta o dostęp, kliknij Zezwól.",
    "Use “Add computer by IP address…” instead.": "Zamiast tego użyj opcji „Dodaj komputer po adresie IP…”.",
    "Automatic discovery is unavailable (UDP port {port}: {error}).":
        "Automatyczne wyszukiwanie jest niedostępne (port UDP {port}: {error}).",
    "Version {version}": "Wersja {version}",
    "Older version": "Starsza wersja",
    "update ready": "aktualizacja gotowa",
    "Send files to {name}": "Wyślij pliki do {name}",
    "Update to version {version}": "Aktualizuj do wersji {version}",
    "Forget this computer": "Zapomnij ten komputer",
    "Add computer by IP address": "Dodaj komputer po adresie IP",
    "Type the IP address shown at the top of {app} on the other computer\n(for example 192.168.1.42):":
        "Wpisz adres IP widoczny u góry okna {app} na drugim komputerze\n(na przykład 192.168.1.42):",
    "“{text}” is not a valid IP address.": "„{text}” nie jest prawidłowym adresem IP.",
    "Could not reach {address}.\n\nCheck that {app} is open on that computer, that both computers are on the "
    "same network, and that its firewall allows the app.":
        "Nie udało się połączyć z {address}.\n\nSprawdź, czy {app} jest otwarty na tamtym komputerze, czy oba "
        "komputery są w tej samej sieci i czy zapora zezwala na działanie aplikacji.",

    # Transfer rows
    "Cancel": "Anuluj",
    "Open folder": "Otwórz folder",
    "Remove from list": "Usuń z listy",
    "Sending “{item}” to {name}": "Wysyłanie „{item}” do {name}",
    "Sent “{item}” to {name}": "Wysłano „{item}” do {name}",
    "Sending {n} item to {name}": ("Wysyłanie {n} elementu do {name}", "Wysyłanie {n} elementów do {name}",
                                   "Wysyłanie {n} elementów do {name}"),
    "Sent {n} item to {name}": ("Wysłano {n} element do {name}", "Wysłano {n} elementy do {name}",
                                "Wysłano {n} elementów do {name}"),
    "Receiving “{item}” from {name}": "Odbieranie „{item}” od {name}",
    "Received “{item}” from {name}": "Odebrano „{item}” od {name}",
    "Receiving {n} item from {name}": ("Odbieranie {n} elementu od {name}", "Odbieranie {n} elementów od {name}",
                                       "Odbieranie {n} elementów od {name}"),
    "Received {n} item from {name}": ("Odebrano {n} element od {name}", "Odebrano {n} elementy od {name}",
                                      "Odebrano {n} elementów od {name}"),
    "Updating {name} to version {version}": "Aktualizowanie {name} do wersji {version}",
    "Updated {name} to version {version}": "Zaktualizowano {name} do wersji {version}",
    "Receiving version {version} from {name}": "Odbieranie wersji {version} od {name}",
    "Installed version {version} from {name}": "Zainstalowano wersję {version} od {name}",
    "Starting": "Rozpoczynanie",
    "{done} of {total}": "{done} z {total}",
    "about {time} left": "zostało około {time}",
    "file {current} of {total}": "plik {current} z {total}",
    "{size} in {time}": "{size} w {time}",
    "Done": "Gotowe",
    "Failed": "Błąd",
    "Cancelled": "Anulowano",
    "Declined": "Odrzucono",
    "{n} file": ("{n} plik", "{n} pliki", "{n} plików"),

    # Incoming files
    "Incoming files": "Przychodzące pliki",
    "<b>{name}</b> ({os} · {ip}) wants to send you {files} ({size}).":
        "<b>{name}</b> ({os} · {ip}) chce wysłać Ci {files} ({size}).",
    "{name}   —   folder, {files}, {size}": "{name}   —   folder, {files}, {size}",
    "They will be saved in a new numbered folder inside: {folder}":
        "Zostaną zapisane w nowym, numerowanym folderze w: {folder}",
    "⚠ Not enough free space: only {size} available.": "⚠ Za mało wolnego miejsca: dostępne tylko {size}.",
    "Accept": "Akceptuj",
    "Decline": "Odrzuć",
    "Declines automatically in {seconds} s": "Automatyczne odrzucenie za {seconds} s",

    # Settings
    "Name of this computer:": "Nazwa tego komputera:",
    "Save received files in:": "Zapisuj odebrane pliki w:",
    "Browse…": "Przeglądaj…",
    "Ask me before accepting incoming files (recommended)": "Pytaj przed przyjęciem przychodzących plików (zalecane)",
    "Appearance:": "Wygląd:",
    "Language:": "Język:",
    "Automatic (system language)": "Automatycznie (język systemu)",
    "IP address: {ip}": "Adres IP: {ip}",
    "not connected": "brak połączenia",
    "Port: {port}": "Port: {port}",
    "not listening": "nie nasłuchuje",
    "The new language is used after {app} restarts. Restart now?":
        "Nowy język zostanie użyty po ponownym uruchomieniu aplikacji {app}. Uruchomić ponownie teraz?",

    # Updates
    "Update": "Aktualizuj",
    "Update {name}": "Aktualizuj {name}",
    "Update all ({n})": "Aktualizuj wszystkie ({n})",
    "Restart now": "Uruchom ponownie",
    "Version {version} is ready for {names}.": "Wersja {version} jest gotowa dla: {names}.",
    "{names} can't update automatically (an older or Mac version, or not the packaged app). Download the new "
    "version there from the Releases page.":
        "{names}: automatyczna aktualizacja niemożliwa (starsza wersja, wersja na Maca albo aplikacja uruchomiona "
        "z kodu źródłowego). Pobierz tam nową wersję ze strony Releases.",
    "Version {version} is installed on this computer. Restart the app to start using it.":
        "Wersja {version} jest zainstalowana na tym komputerze. Uruchom aplikację ponownie, aby z niej korzystać.",
    "Update installed. The app restarts as soon as the running transfers finish.":
        "Aktualizacja zainstalowana. Aplikacja uruchomi się ponownie, gdy zakończą się trwające przesyłania.",
    "Update available": "Dostępna aktualizacja",
    "<b>{name}</b> ({ip}) wants to update {app} on this computer from version {old} to <b>{new}</b>.":
        "<b>{name}</b> ({ip}) chce zaktualizować {app} na tym komputerze z wersji {old} do <b>{new}</b>.",
    "The update is signed by your computer and checked before it's installed. The app restarts by itself "
    "afterwards, once any running transfers have finished.":
        "Aktualizacja jest podpisana przez Twój komputer i sprawdzana przed instalacją. Potem aplikacja sama "
        "uruchomi się ponownie, gdy zakończą się trwające przesyłania.",
    "Update now": "Aktualizuj teraz",
    "Not now": "Nie teraz",
    "Answers “Not now” automatically in {seconds} s": "Automatycznie „Nie teraz” za {seconds} s",
    "{n} transfer still in progress. Stop and restart?": (
        "{n} przesyłanie wciąż trwa. Przerwać i uruchomić ponownie?",
        "{n} przesyłania wciąż trwają. Przerwać i uruchomić ponownie?",
        "{n} przesyłań wciąż trwa. Przerwać i uruchomić ponownie?"),
    "{n} transfer still in progress. Stop and quit?": (
        "{n} przesyłanie wciąż trwa. Przerwać i zamknąć?",
        "{n} przesyłania wciąż trwają. Przerwać i zamknąć?",
        "{n} przesyłań wciąż trwa. Przerwać i zamknąć?"),
    "The app couldn't restart by itself. Please open it again.":
        "Aplikacja nie mogła sama uruchomić się ponownie. Otwórz ją jeszcze raz.",

    # Messages from the transfer engine
    "Connecting": "Łączenie",
    "Preparing files": "Przygotowywanie plików",
    "Waiting for {name} to accept": "Czekanie na akceptację przez {name}",
    "Waiting for you to accept": "Czeka na Twoją akceptację",
    "Waiting for the other computer to finish saving": "Czekanie, aż drugi komputer skończy zapisywać",
    "Saved to {folder}": "Zapisano w {folder}",
    "Saved to {folder} ({n} file could not be read on the other computer)": (
        "Zapisano w {folder} (nie udało się odczytać {n} pliku na drugim komputerze)",
        "Zapisano w {folder} (nie udało się odczytać {n} plików na drugim komputerze)",
        "Zapisano w {folder} (nie udało się odczytać {n} plików na drugim komputerze)"),
    "Delivered to {name}": "Dostarczono do {name}",
    "Delivered to {name} ({n} file could not be read and was skipped)": (
        "Dostarczono do {name} (pominięto {n} plik, którego nie udało się odczytać)",
        "Dostarczono do {name} (pominięto {n} pliki, których nie udało się odczytać)",
        "Dostarczono do {name} (pominięto {n} plików, których nie udało się odczytać)"),
    "Nothing to send - the selected files could not be found.":
        "Nie ma czego wysłać – nie znaleziono wybranych plików.",
    "Could not connect to {name}. Make sure the app is open there and that its firewall allows it.":
        "Nie udało się połączyć z {name}. Upewnij się, że aplikacja jest tam otwarta i że zapora na to pozwala.",
    "Could not connect. Is the app open on the other computer?":
        "Nie udało się połączyć. Czy aplikacja jest otwarta na drugim komputerze?",
    "The other computer stopped responding.": "Drugi komputer przestał odpowiadać.",
    "The connection to the other computer was lost.": "Utracono połączenie z drugim komputerem.",
    "The other computer sent unexpected data ({detail}). Are both apps the same version?":
        "Drugi komputer wysłał nieoczekiwane dane ({detail}). Czy obie aplikacje mają tę samą wersję?",
    "{name} was damaged in transit (checksum mismatch)":
        "Plik {name} uszkodził się podczas przesyłania (niezgodna suma kontrolna)",
    "The other computer stopped the transfer.": "Drugi komputer przerwał przesyłanie.",
    "The other computer cancelled the transfer.": "Drugi komputer anulował przesyłanie.",
    "The sender cancelled the transfer.": "Nadawca anulował przesyłanie.",
    "The sender cancelled before you answered.": "Nadawca anulował przed Twoją odpowiedzią.",
    "You cancelled the transfer.": "Przesyłanie zostało anulowane przez Ciebie.",
    "You declined these files.": "Te pliki zostały przez Ciebie odrzucone.",
    "Not answered in time.": "Brak odpowiedzi w wyznaczonym czasie.",
    "The other computer declined.": "Drugi komputer odmówił.",
    "The other computer declined the files.": "Drugi komputer odrzucił pliki.",
    "Nobody answered on the other computer.": "Nikt nie odpowiedział na drugim komputerze.",
    "The other computer could not save the files: {error}": "Drugi komputer nie mógł zapisać plików: {error}",
    "The other computer refused the file list (invalid names).":
        "Drugi komputer odrzucił listę plików (nieprawidłowe nazwy).",
    "The two apps are different versions. Please update both.": "Aplikacje mają różne wersje. Zaktualizuj obie.",

    # Messages from the update engine
    "Waiting for {name} to accept the update": "Czekanie na zgodę {name} na aktualizację",
    "Waiting for you to accept the update": "Czeka na Twoją zgodę na aktualizację",
    "{name} is checking and installing the update": "{name} sprawdza i instaluje aktualizację",
    "{name} now has version {version} and is restarting.":
        "{name} ma teraz wersję {version} i uruchamia się ponownie.",
    "Checking that the new version starts": "Sprawdzanie, czy nowa wersja się uruchamia",
    "Version {version} installed. Restarting…": "Zainstalowano wersję {version}. Ponowne uruchamianie…",
    "You chose not to update now.": "Wybrano „Nie teraz”.",
    "The other computer chose not to update now.": "Na drugim komputerze wybrano „Nie teraz”.",
    "You cancelled the update.": "Aktualizacja została anulowana przez Ciebie.",
    "The other computer cancelled the update.": "Drugi komputer anulował aktualizację.",
    "The sender cancelled the update.": "Nadawca anulował aktualizację.",
    "The update failed on the other computer: {error}": "Aktualizacja na drugim komputerze nie powiodła się: {error}",
    "The update isn't signed by your computer, so it was refused.":
        "Aktualizacja nie jest podpisana przez Twój komputer, więc została odrzucona.",
    "The update information is damaged.": "Informacje o aktualizacji są uszkodzone.",
    "Updates aren't set up in this copy of the app.": "Aktualizacje nie są skonfigurowane w tej kopii aplikacji.",
    "The update has no version for {system}.": "Aktualizacja nie zawiera wersji dla {system}.",
    "That computer already has version {version} or newer.": "Tamten komputer ma już wersję {version} lub nowszą.",
    "That copy of the app can't update itself (it isn't the packaged app, or its folder is read-only). Copy the "
    "new version there by hand.":
        "Ta kopia aplikacji nie może sama się zaktualizować (to nie jest spakowana aplikacja albo jej folder jest "
        "tylko do odczytu). Skopiuj tam nową wersję ręcznie.",
    "The downloaded update doesn't match its signature, so it was discarded.":
        "Pobrana aktualizacja nie zgadza się z podpisem, więc została odrzucona.",
    "The new version didn't start correctly on this computer, so the current version was kept.":
        "Nowa wersja nie uruchomiła się poprawnie na tym komputerze, więc zachowano obecną.",

    # Units, durations, months
    "B": "B", "KB": "KB", "MB": "MB", "GB": "GB", "TB": "TB",
    "{s} s": "{s} s",
    "{m} min {s:02d} s": "{m} min {s:02d} s",
    "{h} h {m:02d} min": "{h} godz. {m:02d} min",
    "Jan": "sty", "Feb": "lut", "Mar": "mar", "Apr": "kwi", "May": "maj", "Jun": "cze",
    "Jul": "lip", "Aug": "sie", "Sep": "wrz", "Oct": "paź", "Nov": "lis", "Dec": "gru",
    # Resuming interrupted transfers
    "Resume": "Wznów",
    "Discard": "Odrzuć",
    "Interrupted": "Przerwano",
    "Resuming": "Wznawianie",
    "It continues by itself when {name} is back online, or click Resume.":
        "Wznowi się samo, gdy {name} znowu będzie online. Możesz też kliknąć Wznów.",
    "It continues when {name} sends the rest.": "Będzie kontynuowane, gdy {name} wyśle resztę.",
    "Checking the part that was already sent": "Sprawdzanie już wysłanej części",
    "Checking the part that already arrived": "Sprawdzanie części, która już dotarła",
    "The transfer was interrupted.": "Przesyłanie zostało przerwane.",
    "The other computer closed the app.": "Na drugim komputerze zamknięto aplikację.",
    "This app was closed during the transfer.": "Aplikacja została zamknięta w trakcie przesyłania.",
    "The other computer stopped this transfer for good.": "Drugi komputer zakończył to przesyłanie na stałe.",
    "The sender stopped this transfer for good.": "Nadawca zakończył to przesyłanie na stałe.",
    "The other computer could not read the files: {error}": "Drugi komputer nie mógł odczytać plików: {error}",
    "Stop this transfer for good? The files that already arrived on {name} stay there.":
        "Zakończyć to przesyłanie na stałe? Pliki, które już dotarły do {name}, zostaną tam.",
    "Stop this transfer for good? The files that already arrived stay in the folder; the unfinished one is deleted.":
        "Zakończyć to przesyłanie na stałe? Pliki, które już dotarły, zostaną w folderze, a niedokończony plik "
        "zostanie usunięty.",
    "{n} transfer still in progress. Restart anyway?\n\nIt continues where it stopped after the restart.": (
        "{n} przesyłanie wciąż trwa. Uruchomić ponownie mimo to?\n\nPo ponownym uruchomieniu będzie "
        "kontynuowane od miejsca przerwania.",
        "{n} przesyłania wciąż trwają. Uruchomić ponownie mimo to?\n\nPo ponownym uruchomieniu będą "
        "kontynuowane od miejsca przerwania.",
        "{n} przesyłań wciąż trwa. Uruchomić ponownie mimo to?\n\nPo ponownym uruchomieniu będą "
        "kontynuowane od miejsca przerwania."),
    "{n} transfer still in progress. Quit anyway?\n\nIt continues where it stopped the next time both computers have the app open.": (
        "{n} przesyłanie wciąż trwa. Zamknąć mimo to?\n\nBędzie kontynuowane od miejsca przerwania, gdy "
        "aplikacja będzie znowu otwarta na obu komputerach.",
        "{n} przesyłania wciąż trwają. Zamknąć mimo to?\n\nBędą kontynuowane od miejsca przerwania, gdy "
        "aplikacja będzie znowu otwarta na obu komputerach.",
        "{n} przesyłań wciąż trwa. Zamknąć mimo to?\n\nBędą kontynuowane od miejsca przerwania, gdy "
        "aplikacja będzie znowu otwarta na obu komputerach."),
}
