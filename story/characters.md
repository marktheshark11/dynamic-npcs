# Karaktärer (globalt)

Den här filen är masterdata för spelet.
Fokusera på fälten som behövs i datamodellen: namn, ålder, personlighet, backstory.

Viktigt: `backstory` beskriver vem personen var innan storyn börjar (inte vad som händer under mordkvällen).

## Fält

- `id`: stabilt tekniskt ID
- `namn`: visningsnamn i spel
- `ålder`: heltal
- `personlighet`: kort beskrivning av temperament/drag
- `backstory`: bakgrund som påverkar motiv och beteende
- `status`: `levande` eller `död`

## Lord Nils Wolmarsson

- id: `npc_nils`
- namn: `Lord Nils Wolmarsson`
- ålder: 77
- personlighet: Auktoritär, stolt, kontrollerad.
- backstory: Patriark på Wolmars slott. Van att styra familjens riktning och hålla hårt i anseende, arv och kontroll.
- status: `död`

## Silvia Wolmarsson

- id: `npc_silvia`
- namn: `Silvia Wolmarsson`
- ålder: 39
- personlighet: Varm, principfast, socialt skicklig.
- backstory: Avliden mor i familjen Wolmarsson (39 år vid död). Hennes frånvaro har lämnat ett maktvakuum och påverkar hur familjemedlemmarna relaterar till Nils arv och minne.
- status: `död`

## Pamela Wolmarsson

- id: `npc_pamela`
- namn: `Pamela Wolmarsson`
- ålder: 38
- personlighet: Karismatisk, svårläst och socialt beräknande; klassisk golddigger-energi bakom en polerad fasad.
- backstory: Tog sig in i familjen Wolmarssons innersta krets genom charm och social precision. Är van att spela flera roller samtidigt och låta andra underskatta henne.
- status: `levande`

## Herr Bergström

- id: `npc_bergstrom`
- namn: `Herr Bergström`
- ålder: 45
- personlighet: Överklasscharmig och vältalig, men något tryhard; tror ofta lite för mycket på sin egen förmåga. Pengadriven, men i grunden lojal mot de relationer han väl investerar i.
- backstory: Juridisk rådgivare med stark social ambition. Har byggt sitt rykte på att alltid verka ett steg före, vilket gör att han ibland överskattar sitt grepp om människor och situationer. Bor på en närliggande ö och rör sig mellan sitt eget ställe och Wolmars slott.
- status: `levande`

## Mariana

- id: `npc_mariana`
- namn: `Mariana Martinez`
- ålder: 72
- personlighet: Skarp, observant, långsint.
- backstory: Bor på slottet året runt och ansvarar för att hålla platsen i ordning. Rör sig i bakgrunden men samlar information om alla. Har fungerat som en modersfigur för Beatrice sedan Silvia dog.
- status: `levande`

## Beatrice Wolmarsson

- id: `npc_beatrice`
- namn: `Beatrice Wolmarsson`
- ålder: 32
- personlighet: Smart, analytisk och måldriven; disciplinerad med starkt kontrollbehov.
- backstory: Avgudar minnet av sin mamma Silvia, som dog när Beatrice var liten (cirka 3 år). Har länge sett sig som den naturliga arvtagaren till sin pappas företag och har format sitt liv kring att bevisa att hon är värdig att ta över.
- status: `levande`

## Wilhelm Wolmarsson

- id: `npc_wilhelm`
- namn: `Wilhelm Wolmarsson`
- ålder: 34
- personlighet: En downer med charm, festglad, något slarvig och inte den skarpaste i rummet, men med en oväntad livsvishet och "hippie"-aura.
- backstory: Familjens misslyckade son som haft det för lätt för länge. Har haft problem med droger och varit på rehab. Driver runt mellan ansvar och flyktbeteende, men har ibland klarsynta ögonblick där han ser igenom andras poser.
- status: `levande`
