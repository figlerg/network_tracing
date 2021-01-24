Seminar at TU Vienna: Contact Tracing, Epidemiology, Mathematical Modeling

Author: Felix Gigler



Installation:
	install miniconda, then (in Anaconda Terminal):

	conda install numpy matplotlib networkx scipy ffmpeg

Note for visualizations:
	beginninng with 07.01.2021 I try to name visualizations such that at some point it includes <nr of nodes>_<p> in order to keep track of network params

Note for experiments:
	if nothing happens when calling "simple_experiment", chances are that the results for these params are already computed and pickled in 'Experiments' folder.

Some notes about experiments are in "notes.txt" inside the experiments folder!

Current targets:

	Mach ein paar Parametervariationen,  insbesondere für die(den) netzwerkbezogenen Parameter und schau nach, wie sich die Infektionszahlen (Zeitreihe der Summe deiner gelben/roten punkterln) verändern. Hierzu wirst du Monte Carlo simulation machen müssen - also schalt den visuellen Output aus, sonst wirst du alt dabei;).

	Implementier eine Quarantänemodell: Jeder rot-gewordene Punkt triggert sich eine gewisse Zeit nach seiner rot-werdung ein quarantäne Event das seine Kanten für eine gewisse Zeit für transmissionen disabled.

	Implementier ein Tracingmodell. Jeder kontaktpartner eines rot-gewordene Punkts triggert sich eine gewisse Zeit nach dessen rot-werdung ein quarantäne Event das seine Kanten für eine gewisse Zeit für transmissionen disabled.
