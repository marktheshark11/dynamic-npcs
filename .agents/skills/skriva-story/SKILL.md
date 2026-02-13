---
name: skriva-story
description: Hjalp anvandaren att skriva en sammanhangande whodunnit steg for steg.
---

# SKILL: skriva-story

## Syfte

Hjalp anvandaren att skriva storyn bit for bit over en hel dag, sa att hela forlopet
till slut ar tackt ur alla karaktarers perspektiv.
Fokus ar logik + dramatik + tydliga perspektiv (sanning, missforstand, logner).

## Obligatoriska regler

- Du far vara kreativ och foresla vad som kan handa, men fraga alltid anvandaren
  innan forslaget blir en last storyfakta.
- Markera tydligt skillnad mellan:
  - `Last fakta`
  - `Forslag (ej last)`
- Nar nagot ar oklart: skriv `[att fylla i]`.
- Bekrafta efter varje steg vad som ar last sanning.

## Arbetsfiler

- `story/main_story.md`
- `story/characters.md`
- `story/relations.md`
- `story/mysteries.md`

## Hur vi jobbar i praktiken

1. **En liten bit at gangen**
   - Skriv i mycket sma delar: en tidpunkt, en micro-scen eller en tydlig handelse.
   - Maltillstand: hela dagen ar kartlagd stegvis, fran flera perspektiv.
2. **Uppdatera filer direkt**
   - `main_story.md`: handelser i ordning (objektiv + perspektiv), del for del.
   - `characters.md`: endast karaktarsdata/masterdata (inte nya handelser i storyn).
   - `relations.md`: korta riktningsrader (`A -> B`).
3. **Fraga en tydlig detaljfraga vidare**
   - Exakt tid, vem som var dar, vad som sades, vad som doldes,
     och vilken karaktar vi foljer nasta bit.

## Arbetsloop for varje bit

1. Valj en liten tidsbit (t.ex. `14:10-14:20`).
2. Skriv/uppdatera objektiv handelse i `main_story.md`.
3. Skriv/uppdatera berorda karaktarers perspektiv i tidsordning.
4. Om fakta saknas: ge 1-3 kreativa forslag som `Forslag (ej last)`.
5. Fraga anvandaren vilket forslag som ska lasas (eller om nytt forslag onskas).
6. Bekrafta vad som nu ar `Last fakta`.

## Struktur vi foljer

### main_story.md

- Folj filens rubriker och ordning.
- Objektiv story i tidsordnad bullet-lista.
- Perspektiv per karaktar, ocksa i tidsordning.
- Storyn skrivs del for del med fokus pa att till slut tacka hela dagen.
- Hall isar:
  - `Lasta fakta`
  - `Oppna punkter`
  - `Forslag (ej last)`

### characters.md

Ska spegla speldata:

- id
- namn
- alder
- personlighet
- backstory (innan storyn startar)
- status

Viktigt:

- Folj exakt den struktur som finns i filen.
- Uppdatera endast om anvandaren faktiskt vill andra masterdata.
- Anvand inte `characters.md` for handelser under dagen.

### relations.md

Simpelt format:

- `Karaktar A -> Karaktar B`
- Offentlig ton
- Privat asikt
- Dold agenda/logn

## Whodunnit-kvalitet (kontroll)

- Maste finnas trovardig motiv + mojlighet + tillgang.
- Minst 2-3 rimliga alternativa misstankta.
- Ledtradar ska kunna feltolkas innan upplosningen.
- Upplosningen ska kannas rattvis i efterhand.

## Definition of Done

Storyn ar redo nar:

- hela dagen ar tackt i sma tidsbitar,
- varje huvudkaraktar har ett sammanhangande perspektiv i tidsordning,
- tidslinjen hanger ihop utan logiska glapp,
- relationer driver konflikter pa ett konsekvent satt,
- allt som ar osakert ar markerat som `[att fylla i]` eller `Forslag (ej last)`.
