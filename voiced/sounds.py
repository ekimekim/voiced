
import logging

from .util import run_command


# Canned sound library
ACK = '/home/mike/random/beep-ack-2.wav'
QUESTION = '/home/mike/random/beep-question-3.wav'
ERROR = '/home/mike/random/beep-error.wav'


def play(filename):
	logging.debug("Playing file: {}".format(filename))
	with open(filename) as f:
		play_fileobj(f)


def play_fileobj(fileobj):
	"""Play given file object containing audio data. Must be a real file (ie. with a fileno),
	not a file-like object."""
	run_command(
		"ffplay",
		"-hide_banner", "-nodisp", "-nostats", "-loglevel", "error",
		"-autoexit",
		"-", # stdin
		stdin=fileobj,
	)


def speak(text):
	"""Say given text out loud"""
	logging.debug("Saying text: {}".format(text))
	run_command("espeak-ng", text)
