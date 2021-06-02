
import logging

from gevent.subprocess import PIPE, Popen


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
	proc = Popen([
		"ffplay",
		"-hide_banner", "-nodisp", "-nostats", "-loglevel", "error",
		"-autoexit",
		"-", # stdin
	], stdin=fileobj, stderr=PIPE)
	try:
		_, stderr = proc.communicate()
		if proc.wait() != 0:
			raise Exception("ffmpeg exited with status: {}\n{}".format(proc.returncode, stderr))
	finally:
		try:
			if proc.poll() is None:
				proc.kill()
		except EnvironmentError:
			pass
