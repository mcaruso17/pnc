# Risorse del Piano Nazionale Complementare per comune

Mappa interattiva degli importi del Piano Nazionale Complementare al PNRR (PNC)
assegnati ai 7.894 comuni italiani: totale e dettaglio per settore di intervento.

**Deliverable:** [`mappa-pnc.html`](mappa-pnc.html) - un unico file HTML autosufficiente
(~1,9 MB). Si apre con un doppio clic, non richiede un server, funziona anche offline
(senza rete usa i font di sistema invece di Titillium Web).

## Cosa contiene la pagina

- Coropleta a livello comunale, con zoom e trascinamento, per il totale PNC o per
  ciascuno dei 21 settori, piu' la voce residuale «Altri interventi non ripartiti».
- Commutatore valore assoluto / euro per abitante.
- 7 classi di pari numerosita' calcolate sui soli comuni con un importo maggiore di
  zero; i comuni senza importo restano in grigio neutro.
- Sui settori con pochi beneficiari (per esempio i porti: 42 comuni) i comuni troppo
  piccoli per essere visibili sono segnalati da un punto.
- Ricerca per nome, classifica dei primi comuni, ripartizione per regione, scheda di
  dettaglio del comune selezionato, esportazione CSV dell'intero dataset.

## Dati

| | |
|---|---|
| Importi | `Dataset PNC.xlsx`, una riga per comune, codice ISTAT a 6 cifre |
| Confini | limiti comunali ISTAT, edizione 1&deg; gennaio 2026, via [openpolis/geojson-italy](https://github.com/openpolis/geojson-italy) (CC-BY) |
| Totale mappato | 15,79 mld di euro su 7.894 comuni |

### Note sulla lavorazione

- **Popolazione.** Non e' una colonna del file: e' ricavata come
  `Totale risorse / Risorse pc`. Il rapporto e' identico su tutte le 22 coppie di
  colonne di ogni riga (scarto massimo 4&times;10<sup>-16</sup>), e la somma nazionale
  torna a 58,94 milioni di abitanti. I valori pro capite sono quindi ricalcolati nel
  browser e coincidono con le colonne `pc` del file.
- **Totale contro somma dei settori.** Il totale di ogni comune e' sempre maggiore o
  uguale alla somma dei 21 settori; a livello nazionale i settori coprono l'89,1% del
  totale. Il residuo (1,71 mld, 10,9%) e' esposto come «Altri interventi non
  ripartiti» invece di essere taciuto.
- **Settori vuoti.** `Digitalizzazione PA` e `Ricerca sanitaria` sono a zero per tutti
  i comuni. Restano nel menu, disattivati, cosi' l'assenza e' visibile.
- **Allineamento dei codici ISTAT.** I codici del dataset corrispondono esattamente
  all'elenco dei comuni in vigore dal 21 febbraio 2026 (7.894 su 7.894). Il file dei
  confini e' l'edizione 1&deg; gennaio 2026 (7.896 comuni), quindi tre poligoni
  soppressi vengono fusi nei successori prima del join: Lirio in Montalto Pavese,
  Castegnero e Nanto in Castegnero Nanto.

## Ricostruire la pagina

```sh
git clone --depth 1 https://github.com/openpolis/geojson-italy ../openpolis/geojson-italy
python3 build/build_site.py      # scrive mappa-pnc.html
python3 build/verify.py          # ricontrolla i valori generati sul workbook
```

Solo libreria standard di Python (nessuna dipendenza da installare). `build/` contiene:

| file | ruolo |
|---|---|
| `build_site.py` | join, semplificazione dei dati, scrittura della pagina |
| `template.html` | struttura, stile e codice della pagina, con il segnaposto `__PNC_DATA__` |
| `xlsx_reader.py` | lettore XLSX minimale basato su `zipfile` + `ElementTree` |
| `verify.py` | confronto fra i valori nella pagina e il workbook di partenza |

Il percorso del file dei confini, del workbook e dell'output si cambiano con
`--topojson`, `--xlsx` e `--out`.

## Avvertenza

Elaborazione indipendente. Non e' una pubblicazione del Ministero dell'Economia e
delle Finanze ne' della Ragioneria Generale dello Stato; lo stile grafico e' ispirato
alle pagine istituzionali ma non ne riproduce marchi o loghi.
