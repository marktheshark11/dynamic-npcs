# Karaktärer (globalt)

Den här filen är masterdata för spelet.
Fokusera på fälten som behövs i datamodellen: namn, ålder, personlighet, bakgrund.

Viktigt: `bakgrund` beskriver vem personen var innan storyn börjar (inte vad som händer under mordkvällen).

## Fält

- `id`: stabilt tekniskt ID
- `namn`: visningsnamn i spel
- `ålder`: heltal
- utseende: kort beskrivning, hårfärg, små detaljer
- `personlighet`: kort beskrivning av temperament/drag
- `status`: `levande` eller `död`
- `utseende` : deskription av karaktärens utseende
- `bakgrund`: bakgrund som påverkar motiv och beteende

## Lord Nils Wolmarsson

- id: `npc_nils`
- namn: `Lord Nils Wolmarsson`
- ålder: 77
- utseende: Kraftigt överviktig, brunhårig, bruna ögon, brun grått skägg, Hud: blek, rosig, lätt svettig panna, ser fragil ut.
- personlighet: Auktoritär, stolt, kontrollerad.
- status: `död`

- bakgrund: Lord Nils Wolmarsson formades av en sträng uppväxt där kontroll och plikt stod över allt. Han bär slottet och familjenamnet som ett ansvar snarare än en förmån, och ser arv som något man måste skydda med disciplin och hårda gränser. Slottet byggdes under den tid då hans morfar levde; det ärvdes först av Nils far och gick därefter vidare till Nils, vilket förstärkte hans känsla av att han bara förvaltar något större än sig själv. I dag använder Nils slottet som sitt sommarhus, medans han bor på Östermalm i Stockholms innerstad.

Lord Nils Wolmarsson var verkställande direktör för det pappersindustriföretag som hans far hade grundat. Han innehade rollen med en tydlig betoning på plikt, ordning och ansvar, och såg företaget som en central del av familjens arv och ställning.

Han gifte sig med Silvia vid 25 och hennes värme fungerade länge som motvikt till hans kyliga auktoritet. Efter hennes död blev han ännu mer kontrollerande och misstänksam; sorgen tog formen av regler, rutiner och ett behov av att ha grepp om människor runt sig.

Lord Nils Wolmarsson träffade Pamela, som var 39 år yngre än honom, för fyra år sedan. De inledde en relation och gifte sig efter ett år tillsammans.

Han ser Beatrice som den naturliga arvtagaren och har pressat henne att bli skarp och värdig, medan Wilhelm blivit hans stora besvikelse: charmig men ansvarslös, med en historia av missbruk och flykt. Nils är stolt och lojal mot “sitt”, men skapar rädsla omkring sig. Hans största drivkraft är rädslan att allt han byggt ska falla sönder när han försvinner.

## Silvia Wolmarsson

- id: `npc_silvia`
- namn: `Silvia Wolmarsson`
- ålder: 39
- utseende: Blond, blåögd, kort, vacker
- personlighet: Varm, principfast, socialt skicklig.
- bakgrund: Avliden mor i familjen Wolmarsson (39 år vid död). Hennes frånvaro har lämnat ett maktvakuum och påverkar hur familjemedlemmarna relaterar till Nils arv och minne.
- status: `död`


## Pamela Wolmarsson

- id: `npc_pamela`
- namn: `Pamela Wolmarsson`
- ålder: 38
- utseende: Blond hårig, blåa ögon, välklädd, handväska, solglasögon
- personlighet: Karismatisk, svårläst och socialt beräknande; klassisk golddigger-energi bakom en polerad fasad.
- bakgrund: Tog sig in i familjen Wolmarssons innersta krets genom charm och social precision. Är van att spela flera roller samtidigt och låta andra underskatta henne.
- status: `levande`

## Herr Bergström

- id: `npc_bergstrom`
- namn: `Herr Bergström`
- ålder: 45
- utseende: Brunhårig, backslick, grönögd, lång, stilig, vackert leende.
- personlighet: Överklasscharmig och vältalig, men något tryhard; tror ofta lite för mycket på sin egen förmåga. Pengadriven, men i grunden lojal mot de relationer han väl investerar i.
- bakgrund: Juridisk rådgivare med stark social ambition. Har byggt sitt rykte på att alltid verka ett steg före, vilket gör att han ibland överskattar sitt grepp om människor och situationer. Bor på en närliggande ö och rör sig mellan sitt eget ställe och Wolmars slott.
- status: `levande`

## Mariana

- id: `npc_mariana`
- namn: `Mariana Martinsson`
- ålder: 72
- utseende: Grå hårig, kraftig, kort, rynkig, glasögon, klär sig som en hushållerska men mysig. 
- personlighet: Skarp, observant, långsint.
- bakgrund: Bor på slottet året runt och ansvarar för att hålla platsen i ordning. Rör sig i bakgrunden men samlar information om alla. Har fungerat som en modersfigur för Beatrice sedan Silvia dog.
- status: `levande`

## Beatrice Wolmarsson

- id: `npc_beatrice`
- namn: `Beatrice Wolmarsson`
- ålder: 32
- utseende: Blond, blåögd, lång, elegant klädd, glasögon, 
- personlighet: Smart, analytisk och måldriven; disciplinerad med starkt kontrollbehov.
- bakgrund: Avgudar minnet av sin mamma Silvia, som dog när Beatrice var liten (cirka 3 år). Har länge sett sig som den naturliga arvtagaren till sin pappas företag och har format sitt liv kring att bevisa att hon är värdig att ta över.
- status: `levande`

## Wilhelm Wolmarsson

- id: `npc_wilhelm`
- namn: `Wilhelm Wolmarsson`
- ålder: 34
- utseende: Brun hårig, brunögd, långt ofixat hår, slappa kläder.
- personlighet: En downer med charm, festglad, något slarvig och inte den skarpaste i rummet, men med en oväntad livsvishet och "hippie"-aura.
- bakgrund: Familjens misslyckade son som haft det för lätt för länge. Har haft problem med droger och varit på rehab. Driver runt mellan ansvar och flyktbeteende, men har ibland klarsynta ögonblick där han ser igenom andras poser.
- status: `levande`

## Detektiven


- id: `npc_detektiv`
- namn: `insert_String`
- ålder: `insert_Int`
- utseende: Kort, spänstig byggnad med ett ansikte som är svårt att placera, varken ungt eller gammalt, varken maskulint eller feminint. 
Håret är silvergrått trots åldern och alltid lite för perfekt kammat åt ena sidan. Bär alltid på ett litet, brunslitet anteckningsblock som aldrig verkar lämna handen.
- status: `levande`
