# Co-constructions - Detailed Specification

T2. co-constructed syntax and handling of overlap

We consider as co-constructions those syntactic relations (without any restrictions) that hold between utterances produced (i) by different speakers or (ii) by the same speaker but after an interruption by another speaker. In interactive scenarios, indeed, multiple speakers may intertwine their utterances, sometimes even perfectly overlapping (Lerner 1991, Sacks 1992, Ono & Thompson 1996, Helasvuo 2004, Calabria 2023)

A coconstruction is encoded by a feature on the root of the second utterance indicating the syntactic role of the second utterance towards the first utterance, the sent-id of the first utterance, and the token-id of the governor of the second utterance:

Coconstruct=<deprel>::<sent-id>::<token-id>

When the co-construction involves two or more different speakers, we identify two cases:

Speaker B realizes a syntactic dependency that is already part of the tree built by Speaker A. We can distinguish the following 3 subcases:

A.1. Speaker A leaves a syntactic dependency unrealized and Speaker B offers a completion to what Speaker A started, as in (1). 

Cuz 31 (Ono & Thompson 1996: 72)

L: his position is pretty uh

A: … % (TSK) (H) stable.

    … yeah

A.2. The same syntactic dependency is realized by both speakers, because Speaker A (at some point) completes what s/he started, possibly after a false start or some planning problems. This case frequently results in overlapping between Speaker A and Speaker B realizing the same slot, and as in (2) and (3).

BOD2018 - KIParla

BO118:	c'è architettu:ra::, c' è:::: [ingegneri~]

		there’s architecture there’s engineer-

BO140: 	[ingegn~ ingegn]eria: sì

		enginee- engeenering yes

BO118: 	si che è [molto buona] anche

		yes which is very good too

BOA3017 - KIParla

BO139 quando si parlano sopra

		when they speak one over the other

devi mettere delle parentesi quadre intorno alle parole

	you have to put square parentheses around words

BO146	ah okay

BO139	che si sovrappongono

	that overlap

BO136	come nei sottotitoli

	like in subtitles

BO139	esatto // infatti io (.) [sto]

	exactly // actually I am

BO147	[>in<fatti te po]tresti fare il sotto~ quello che fa i sotto[titoli]  

	actually you could be a subtitler the person who makes subtitles

BO146	[pure te]

	you too

BO145	[sottotitolato]re

	subtitler

A.3.The same syntactic dependency is realized by both speakers, because Speaker A completes their own tree, and Speaker B, in a subsequent turn, selects a syntactic dependency in Speaker’s A tree and realizes it again, either by repeating the content (e.g. for confirmation) or by replacing it (e.g. for correction, as in (5)).

KPS021 - KIParla 

PKP126:	quindi l~ la linea tra finzione e realtà

		so the line between fiction and reality

	cioè tra verità non verità non ho ancora capito [dove sta]

	I mean between truth and non-truth I still haven’t understood where it lies

PKP125:	[più tra de]tto e non detto [x]

		more between said and unsaid

Coconstruction in French-Rhapsodie:

conj:dicto corresponds to A2 cases: speaker-based, dependency-based 

discourse corresponds to backchannel or yes-no answers: speaker-based / dependency-based

The distinction between A and B concerns the achievement of the first speech turn. It can be indicated by a special feature or a punctuation mark. In Rhapsodie, incomplete utterances finish with “…”.

B. Speaker B realizes a syntactic dependency that is NOT already part of the tree built by Speaker A,  adding an additional syntactic dependency to the syntactic tree built by Speaker A

 Lam 23 (Ono & Thompson 1996: 81)

M: they must know each other.

J:  …()oo=.

H: … very well.

    <@ in fact @>

BOA3017 - KIParla

BO139 quando si parlano sopra

		when they speak one over the other

devi mettere delle parentesi quadre intorno alle parole

	you have to put square parentheses around words

BO146	ah okay

BO139	che si sovrappongono

	that overlap

BO136	come nei sottotitoli

	like in subtitles

Cases A and B may be observed also when the co-construction involves the same speaker after an interruption by another speaker, as in (9):

BOD2018 - KIParla

BO118:	c'è architettu:ra::, c' è:::: [ingegneri~]

		there’s architecture there’s engineer-

BO140: 	[ingegn~ ingegn]eria: sì

		enginee- engeenering yes

BO118: 	si che è [molto buona] anche

		yes which is very good too

BOA3017 - KIParla

BO139 quando si parlano sopra

		when they speak one over the other

devi mettere delle parentesi quadre intorno alle parole

	you have to put square parentheses around words

BO146	ah okay

BO139	che si sovrappongono

	that overlap

BO136	come nei sottotitoli

	like in subtitles

The guiding criterion is whether it is possible to apply the ‘if you can link, link’ principle: 

if a tree can be linked to a previous tree uttered by a different speaker or by the same speaker but not consecutively, then use the coconstruct relation;

if a tree can be linked to a previous tree uttered by the same speaker consecutively, then merge the trees.

if the intervention by Speaker B is fully overlapping, that is, Speaker B does NOT interrupt Speaker A, then merge and move Speaker B’ unit after (as in (10))

BOD2018 - KIParla

BOD140: 	i primi anni son più belli si condivide sempre di [più] sei ancora nella fase del

		the first years are nice you always share more you are still in the phase of

siamo tutti amici

		we are all friends

BOD118:	[sì]

		yes

This implies the fact that two dimensions need to be considered: a speaker-dependent one, which only accounts for language uttered by the speaker over time, and a time-dependent one, which accounts for the participation of multiple speakers to the same speech unit.

This is a relatively new aspect for the UD formalism, as written text is usually only concerned with the former perspective.

Eliminating this aspect from the syntactic analysis of spoken language would however introduce a bias in the comparison with planned or written language, as speaker-dependent vision would hide syntactic relations deriving from contributions given by different speakers in the same time frame, and at the same time result in sentence-like units that can only be interpreted (even syntactically) contextually given the contributions of other participants to the interaction.

It is worth remarking that the issue is not entirely new, as for instance social media data might show the same features when it comes to sequences of posts in a thread, possibly posted by different users.

Workshop proposal: provide both speaker-based and dependency-based information, developing a conversion tool to switch between the two "views" and make data available in both versions.

More specifically, in the speaker-based view each speaker utterance is a new tree, and the Speaker ID attribute applied to the tree (# speaker_id metadata).

In the dependency-based view, a tree may be the outcome of multiple speaker concatenations. Each token has a Speaker_id attribute in MISC, as there may be arbitrarily many speakers contributing.

SPEAKER VIEW

# text = I saw a man

# sent_id = s1

# speaker_id = Peter

1	I	PRON	2

2	saw	VERB	0

3	a	DET	4

4	man	NOUN	2

# text = who was wearing a hat

# sent_id = s2

# speaker_id = Maria

1	who	SCONJ	3

2	was	AUX	3

3	wearing	VERB	0	Coconstruct=acl:relcl::s1::4

4	a	DET	5

5	hat	NOUN	3

# text = Sure

# sent_id = s3

# speaker_id = Peter

1	Sure	INTJ	0	Backchannel=s2::3

-------

DEPENDENCY VIEW

# text = I saw a man who was wearing a hat Sure

# sent_id = s1

1	I	PRON	2	Speaker_id=Peter

2	saw	VERB	0	Speaker_id=Peter

3	a	DET	4	Speaker_id=Peter

4	man	NOUN	2	Speaker_id=Peter

5	who	SCONJ	7	Speaker_id=Maria

6	was	AUX	7	Speaker_id=Maria

7	wearing	VERB	4	Coconstruct=Yes|Speaker_id=Maria

8	a	DET	9	Speaker_id=Maria

9	hat	NOUN	7	Speaker_id=Maria

10	Sure	INTJ	7	Backchannel=Yes|Speaker_id=Peter

-------

SPEAKER VIEW

# text = I saw a man

# sent_id = s4

# speaker_ID = Peter

1	I	PRON	2

2	saw	VERB	0

3	a	DET	4

4	man	NOUN	2

# text = M-hm

# sent_id = s5

# speaker_id = Paul

# speech_turn = Outside

1	M-hm	INTJ	0	Backchannel=s4::3

# text = who was wearing a hat

# sent_id = s6

# speaker_id = Maria

# speech_turn = Begin

1	who	SCONJ	3

2	was	AUX	3

3	wearing	VERB	0	Coconstruct=acl:relcl::s4::4

4	a	DET	5

5	hat	NOUN	3

# text = Sure

# sent_id = s7

# speaker_id = Peter

1	Sure	INTJ	0	Backchannel=s6::3

References

Ono, Tsuyoshi, Thompson, Sandra A., 1996. Interaction and Syntax in the Structure of Conversational Discourse: Collaboration, Overlap, and Syntactic Dissociation. In: Hovy, Eduard H. Scott, Donia R. (Eds.), Computational and Conversational Discourse: Burning Issues – An Interdisciplinary Account. Springer, Berlin.

Backchannelling

Backchannels are short productions uttered by one participant in the conversation when the other participants occupy the floor (back-channel vs front-channel). In order to be recognised as BC, a specific utterance must:

be addressed to the content of the utterance produced by the other speaker

not be required or expected based on previous turn (e.g. answers to questions are expected and required, so they cannot be considered BC, see ex. 3)

not require a reaction from the other speaker (see ex. 1, where the speaker continues)

At their core, these verbal reactions show that the speaker has heard the contribution of the partner, often adding that it has been understood and accepted (see Mereu et al. 2024 and Ward and Tsukahara 2000)

(1) Example of BC - BOA3017, KIParla

BO145:[ma] per[ché mamma c'ha dei <pre]giudizi nei miei confronti> da quando (sono) nata

 but because mum has had some prejudices towards me since I was born

 p[enso]

 I think

BO139: [mhmh]

BO145: e poi daniela non devi avere pregiudizi su di me io <io>

	 and then daniela you musn’t have prejudices about me I

(2) Example of BC - BOD2018, KIParla

BO118: [sì] sì ma anch'io:: però era proprio l'esigenza [de sta da sola 

 yes yes me too I also have the need to be alone

 in dei momenti]

 sometimes

BO140: [sì di stare da so:la di non] parla~ di non vedere in faccia [nessuno] 

	 yes to be alone not to speak to see nobody’s face

 di:: di stare per::,

 to be

(3) Example of polar reply - BOA3017, KIParla

BO145 [(non) prendi l'insalata?]x@x@

	won’t you have some salad?

BO139	[sì sì]

	yes yes

BO145	[l’ho mangiata tu]tta io

	I have eaten it all myself

BC may have different forms (paraverbal and verbal), such as mh, mhmh, yes, exactly, right.

In speaker view, tokens that form backchannels should be identifiable by an attribute in the misc column (Backchannel=Yes).
In dependency-based view, tokens are linearly placed based on time alignment to their closest token in time, when such information is available. Syntactically, backchannelling enters the syntactic flow and is linked by a discourse relation. 

discourse:backchannel is introduced as a new dependency sub-label, but should only be used in the cross-speaker case (i.e. when the backchannel has a different speaker ID to its syntactic parent).

In case of backchannel, we consider that the main speaker keeps the speech turn, its utterance is not interrupted and has not to be segmented. The backchannel will be placed in a separate sentence.

TBD: who is the parent node? It could be attached to the root of the preceding utterance, because in some sense it validate the fact it has been received by the adressee

Ludovica: sometimes the speaker uses backchannel to take the floor, i.e. the backchannel gives feedback to another speaker and is used to keep the turn. In this case going from speaker view to dependency view means splitting a sentence and producing two sentences in output.

In Rhapsodie, a backchannel is encoded by a relation discourse between two speaker-based sentences: https://universal.grew.fr/?custom=693004bc2b1d1

We propose to use the relation discourse:backchannel in the dependency-based view.

Encoding: In the speaker-based view, the backchannel has a feature: 

Backchannel=<sent-id>::<token-id>

It is attached to the root of the sentence or phrase that is “validated” by the backchannel.