# Co-constructions and Backchannels in SST Corpus

Kontekst: znotraj UniDive T1.5 si prizadevamo za poenotenje pristopov k slovničnemu razčlenjevanju govorjenega jezika. Med številnimi tipično govorjenimi pojavi, kjer bi želeli stvari poentotiti sta tudi dva, kjer mi trenutno še nimamo prav eksplicitnih oznak, s katerimi bi jih zlahka priklicali iz korpusa: t.i. odzivi (npr. mhm, ja, ipd., angl. backchannels) in t.i. so-strukture (angl. co-constructions). 

Cilj naloge: poiskati primere tovrstnih struktur v korpusu SST in jih označiti, kot predlagano v dokumentu spodaj.

Podrobnosti: v ta dokument sem ti prilepila (neurejeno) razpravo, ki smo jo imeli o teh izrazih, kjer lahko najdeš podrobnejšo definicijo, primere in predlog novega označevanja (+ veliko delovnih komentarjev, ki jih lahko ignoriraš). Ampak v grobem velja:

sostrukture so primeri, kjer drugi govorec dopolni oz. dokonča neko nezaključeno skladenjsko strukturo prvega govorca, npr.

A: no, in potem greva in kar naenkrat vidiva Ano in

B: Petra? Ne moreš verjet.

odzivi (potrditveni signali?) so primeri rabe diskurznih označevalcev (npr. besedic aha, mhm, ja ipd.), s katerimi naslovnik da vedeti poslušalcu, da ga posluša in razume, ampak ne želi prevzeti vloge govorca - prvotni govorec normalno nadaljuje. Primer:

A: hodiva in potem kar neankrat vidiva ano in petra

B: aha

A: in jima rečeva živjo 

Naloga: tvoja naloga bi bila razviti metodo za priklic čim večjega števila primerov obeh pojavov (idealno vseh), jo implementirati in pri tem eksplicitno označiti primere v novi verziji SST, kot predlagano v polinkani razpravi pod ‘speaker view’. Konkretno:

z dodajanjem lastnosti Coconstruct= v stolpec MISC za sostrukture

z dodajanjem Backhannel=  v stolpec MISC za potrditvene signale

Kako se tega dejansko lotiti? To je prvi del naloge / izziva, kjer imaš proste roke za razmislek in implementacijo. Nekaj predlogov pa spodaj …

Coconstructions:

Stanje v SST: tega nikoli nismo posebej eksplicitno označevali in so take strukture zagotovo v različnih izjavah (izjava A, potem izjava B), saj celoten SST temelji na t.i. speaker-view principu: če je nekaj izrezel nek drug govorec, potem je to začetek neke nove izjave. Če so bile kakšne izjave nezaključene (primer A), imamo nekaj smernic, kako to označiti (glej zadnjo verzijo tukaj, npr. pod orphan oz. če iščeš nedokonč*, nezaklj*), tako da je mogoče to lahko posredni signal. V vsakem primeru predpostavljamo, da je primerov teh sostruktur v podatkih malo.

Kako poloviti sostrukture? Začeli bi lahko s tem, da poiščemo pare izjav, kjer je prva izjava od enega govorca, naslednja pa od drugega (torej drugačen speaker_id). Če je tega preveč za ročni pregled, pa razmisliti o hevristikah na podlagi smernic (npr. iskanje relacije orphan v zaključnih delih izjave). Nives: dodatni predlogi dobrodošli.

Backchannels:

Stanje v SST: tega nismo nikoli posebej označevali, saj vse označevalce obravnavamo enako: bodisi kot discourse, če so del neke daljše izjave, bodisi kot root, če se pojavljajo samostojno oz. v družbi z drugimi označevalci. Se pravi enako označujemo ja v vlogi takega potrditvenega signala (backhannel) kot ja v vlogi odgovora na vprašanje (ni backchannel). 

Kako poloviti te potrditvene signale? Začeli bi lahko s tem, da poiščemo pare izjav, kjer je prva izjava od enega govorca, naslednja pa od drugega (torej drugačen speaker_id). V tej drugi izjavi bi se morali ti označevalci pojaviti samostojno (npr. celotna izjava samo ja ali ja ja ja).

O formatih - Bruno:

For the annotation, Rhapsodie and Kiparla annotated the Speaker-based view with features in MISC and the dep-based view is produced automatically. You can do the same for Slovenian.

With the format:

 - Coconstruct=deprel::sent_id::token_id 

ex in Rhapsodie: Coconstruct=mod::Rhap_D0004-62::1    

 - Backchannel=sent_id::token_id (the deprel is always discourse:backchannel)

ex in Kiparla: Backchannel=BOA3017_61::3