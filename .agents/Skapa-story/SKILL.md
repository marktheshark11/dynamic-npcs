# SKILL: Skapa story-seed

## Syfte

Denna skill hjalper till att omvandla skrivna story-filer i `story/` till seed-data i `db/seeds/`.
Fokus ar att bevara ton, konflikter och tvetydighet, men samtidigt skapa konsistent graph-data.

## Input

Las i forsta hand:

- `story/main_story.md`
- `story/characters.md`
- `story/INDEX.md`
- aktuell mysteriemapp, t.ex. `story/mysteries/otroheten/`
  - `overview.md`
  - `characters.md`
  - `items.md`
  - `scenes.md`
  - `clues.md`
  - `timeline.md`

## Output

Skapa/uppdatera en seed-fil i `db/seeds/<mystery>.py` med:

1. NPCs
2. OBJECTs
3. PLACEs
4. EVENTs (om de finns i storyn)
5. MYSTERY
6. CLAIMS
7. REFERENCES
8. OPINIONS (`belief_in`, `openness`)
9. PART_OF-lankar mellan claim och mystery

## Arbetsflode

### 1) Extrahera entiteter

- Bygg tydliga listor for NPC, OBJECT, PLACE, EVENT.
- Anvand namn exakt som i storyn.
- Normalisera endast nar det behovs for databas-konsistens.

### 2) Skapa claims

- En claim = ett tydligt pastaende.
- Behall tvetydighet dar storyn avsiktligt ar oklar.
- Markera `type = "relation"` endast for claims om relationer mellan personer.

### 3) Koppla references

- Varje claim ska referera till relevanta noder (NPC/OBJECT/PLACE/EVENT/CLAIM).
- Satt minst en reference per claim om mojligt.

### 4) Fordela opinions

- Satt `belief_in` efter vad figuren tror.
- Satt `openness` efter vad figuren ar villig att prata om.
- Tillat motsatta tecken for att modellera fornekelse/cover story.

### 5) Validera intern logik

- Kontrollera att inga claims saknar target vid references.
- Kontrollera att alla reference-targets existerar.
- Kontrollera att viktiga konflikter faktiskt blir sokbara i RAG.

## Regler

- Andra inte huvudstoryns sanning utan uttrycklig instruktion.
- Om storyn ar oklar: bevara oklarheten i claims i stallet for att gissa fram fakta.
- Hall naming stabil mellan storyfiler och seedfiler.
- Om nya entitetstyper behovs, notera det tydligt innan implementation.

## Snabbkommandon (for samarbete)

- "Gor detta mysterium seed-ready"
- "Extrahera claims fran scenes+clues"
- "Bygg opinionsmatris for alla NPCs"
- "Validera references och peka ut luckor"

## Definition of Done

- Seed-fil kan koras utan manuella handgrepp.
- Alla centrala storybeats finns representerade som claims.
- Minst en tydlig konflikt (motsagelse) finns modellerad dar storyn kraver det.
- Struktur matchar etablerad stil i `db/seeds/otroheten.py`.
