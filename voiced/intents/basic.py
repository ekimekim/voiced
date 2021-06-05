
from ..intent import intent
from ..listen import start_listening
from .. import sounds


@intent("cancel")
def cancel(text):
	"""Do nothing and make no noise. Used as a filler response if you don't actually
	want anything to run after all."""
	return False


@intent("say_this")
def say_this(_):
	"""Intended mostly for testing or for future work chaining other commands.
	Will prompt user for an open-transcription line, then repeat it back."""
	sounds.play(sounds.ACK)
	response = start_listening(open=True).get()
	if response is None:
		# timeout
		return sounds.ERROR
	sounds.speak(response.text)
	return False # no need for confirmation beep, end of speaking serves that role
