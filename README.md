# dvw2leg

Convertitore da **DataVolley 4** (`.dvw`) a **DataVolley 2** (`.leg`).

Disponibile in due versioni:

| File | Uso |
|------|-----|
| `dvw2leg.py` | Script Python da riga di comando |
| `dvw2leg.html` | Interfaccia web, eseguita interamente nel browser |

---

## Utilizzo — Python

```bash
python3 dvw2leg.py partita.dvw              # genera partita.leg
python3 dvw2leg.py partita.dvw output.leg   # output personalizzato
```

Richiede solo Python 3 (nessuna dipendenza esterna).

## Utilizzo — Web

Apri `dvw2leg.html` in Chrome (o Firefox), trascina uno o più file `.dvw` e clicca **Converti e scarica**.  
Tutto avviene nel browser: nessun file viene inviato a server esterni.

---

## Mapping codici

### Skill (tipo azione)

| DV4 | DV2 | Significato |
|-----|-----|-------------|
| S | B | Battuta (serve) |
| R | R | Ricezione |
| E | A | Alzata (set) |
| A | S | Attacco (spike) |
| B | M | Muro (block) |
| D | D | Difesa |
| F | DA+F | Freeball |

### Zone attacco

| DV4 | DV2 |
|-----|-----|
| Q | V |
| H | A |
| O | L |
| U | T |
| T | T |
| M | M |

### Giocatori

- Squadra casa: numero maglia usato direttamente (es. `03`)
- Squadra ospite: numero maglia + 50 (es. maglia 16 → `66`)
- Maglie ospiti > 49: rimappate al primo slot libero ≤ 49 per evitare overflow a 2 cifre

---

## Note

Testato su file reali della Serie A2 maschile (DataVolley 4.2025).  
Il formato `.leg` prodotto è compatibile con DataVolley 2 e software di analisi basati su DV2.
