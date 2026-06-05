# Obsidian MD Copy — Manuale utente

Script Python per la copia selettiva di file Markdown da una cartella sorgente (es. Dropbox) verso la vault Obsidian su iCloud Drive.

**Autore:** Ignazio Rusconi-Clerici

---

## Descrizione

Permette di scegliere quali file `.md` sincronizzare da Dropbox verso Obsidian, con controllo visuale dello stato di ogni file (nuovo, modificato, identico). Evita copie inutili grazie al confronto tramite MD5.

---

## Requisiti

- Python 3.10+
- Solo librerie standard (`tkinter`, `hashlib`, `shutil`, `json`, `pathlib`)
- `path_widgets.py` in `~/Library/CloudStorage/Dropbox/Documenti_IRC/Python/shared/`

---

## Cartelle default

| Ruolo | Percorso |
|---|---|
| Sorgente | `~/Library/CloudStorage/Dropbox/Documenti_IRC/Viaggi` |
| Destinazione | `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Viaggi` |

Le cartelle sono modificabili dalla GUI e vengono salvate in:
```
~/Library/CloudStorage/Dropbox/Documenti_IRC/Python/_config/apps/ObsidianMD/config.json
```

---

## Interfaccia utente

| Elemento | Descrizione |
|---|---|
| **Sorgente** | Cartella Dropbox contenente i file `.md` da copiare |
| **Destinazione** | Vault Obsidian su iCloud Drive |
| **Copia piatta** | Se attivo, copia tutti i file nella radice della destinazione (senza sottocartelle) |
| **Scansiona** | Analizza la sorgente e mostra l'albero dei file con il loro stato |
| **Copia selezionati** | Copia solo i file spuntati |

### Albero dei file

Ogni file viene mostrato con:
- **Checkbox** per includere/escludere dalla copia
- **Stato**: `Nuovo`, `Modificato`, `Identico`
- **Data ultima modifica**
- **Dimensione**

---

## Logica di confronto

Prima di copiare ogni file viene verificato:
1. Il file esiste nella destinazione?
2. Le dimensioni coincidono?
3. L'MD5 è identico?

Solo se almeno una condizione non è soddisfatta il file viene copiato.

---

## Modalità di copia

### Con sottocartelle (default)
Preserva la struttura delle sottocartelle della sorgente:
```
Dropbox/Viaggi/2025/Giappone.md → Obsidian/Viaggi/2025/Giappone.md
```

### Copia piatta
Tutti i file finiscono nella radice della destinazione:
```
Dropbox/Viaggi/2025/Giappone.md → Obsidian/Viaggi/Giappone.md
```

---

## Build come applicativo macOS

| Campo AppBuilder | Valore |
|---|---|
| Nome App | `ObsidianMDCopy` |
| Hidden imports | *(nessuno)* |
| Windowed | ✅ |

---

## Note

- I file `.md` con lo stesso nome in sottocartelle diverse possono collidere in modalità piatta.
- La configurazione viene salvata automaticamente ad ogni copia eseguita.
- Non richiede connessione internet: lavora solo sul filesystem locale.

---

*Versione 1.1.0 — Marzo 2026*
