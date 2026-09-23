# Risorse del Piano Nazionale Complementare per comune

Mappa interattiva degli importi del Piano Nazionale Complementare al PNRR (PNC)
assegnati ai 7.894 comuni italiani: totale e dettaglio per settore di intervento.

**Deliverable:** [`index.html`](index.html) - un unico file HTML autosufficiente
(~2,1 MB). Si apre con un doppio clic, non richiede un server, funziona anche offline
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
- Sovrapposizione opzionale della rete ferroviaria in esercizio, spenta di default,
  con l'alta velocita' distinta in rosso.

## Dati

| | |
|---|---|
| Importi | `Dataset PNC.xlsx`, una riga per comune, codice ISTAT a 6 cifre |
| Confini | limiti comunali ISTAT, edizione 1&deg; gennaio 2026, via [openpolis/geojson-italy](https://github.com/openpolis/geojson-italy) (CC-BY) |
| Ferrovie | `data/ferrovie.geojson`, tracciati OpenStreetMap (ODbL), estratto Italia del 23 settembre 2026 |
| Totale mappato | 15,79 mld di euro su 7.894 comuni |

### Nota sulla rete ferroviaria

Il layer contiene solo le linee di corsa in esercizio, a scartamento ordinario e ridotto
(`railway=rail` e `narrow_gauge`). Sono esclusi i binari di stazione e di scalo (qualsiasi
way con un tag `service`), gli usi industriali, militari e turistici, le linee dismesse,
in costruzione e in progetto, e le reti tranviarie e metropolitane, che a scala nazionale
non sono leggibili.

Le 48.907 way estratte da OSM diventano 3.636 polilinee unendo le tratte che condividono
un estremo, e 56.608 vertici dopo la semplificazione. La geometria e' agganciata alla
stessa griglia di quantizzazione dei confini ISTAT, circa 14,6 m di passo, e la
tolleranza di Douglas-Peucker e' di una unita' di griglia: al di sotto non ci sarebbe
nulla da guadagnare, perche' la griglia stessa e' il limite di precisione. Il costo nella
pagina e' di 0,18 MB, contro 0,58 MB che sarebbero serviti senza semplificare.

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
python3 build/build_site.py      # scrive index.html
python3 build/verify.py          # ricontrolla i valori generati sul workbook
```

`data/ferrovie.geojson` e' versionato, quindi la build non richiede ne' l'estratto OSM da
2,5 GB ne' l'accesso alla rete. Si rigenera solo per aggiornare la geometria:

```sh
pip install osmium
curl -O https://download.openstreetmap.fr/extracts/europe/italy-latest.osm.pbf
python3 build/extract_rail.py italy-latest.osm.pbf
```

La build usa solo la libreria standard di Python; `extract_rail.py`, che si lancia a
parte e di rado, richiede `osmium`. `build/` contiene:

| file | ruolo |
|---|---|
| `build_site.py` | join, semplificazione dei dati, scrittura della pagina |
| `template.html` | struttura, stile e codice della pagina, con il segnaposto `__PNC_DATA__` |
| `extract_rail.py` | estrazione, unione e semplificazione delle ferrovie da un estratto OSM |
| `xlsx_reader.py` | lettore XLSX minimale basato su `zipfile` + `ElementTree` |
| `verify.py` | confronto fra i valori nella pagina e il workbook di partenza |

Il percorso del file dei confini, del workbook e dell'output si cambiano con
`--topojson`, `--xlsx` e `--out`.

## Avvertenza

Elaborazione indipendente. Non e' una pubblicazione del Ministero dell'Economia e
delle Finanze ne' della Ragioneria Generale dello Stato; lo stile grafico e' ispirato
alle pagine istituzionali ma non ne riproduce marchi o loghi.
