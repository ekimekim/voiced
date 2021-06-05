
import json
import logging
from collections import namedtuple

import gevent
from gevent.subprocess import PIPE, Popen


ListenResponse = namedtuple('ListenResponse', ['text', 'intent', 'groups'])


def _run_listener(ready, open, timeout):
	# Note that we might be killed at any time, so we need to ensure we clean up
	# after ourselves.
	procs = []
	try:
		# Start needed processes in parallel.
		# We don't actually need the intent recogniser immediately, but it helps latency
		# if we start it up beforehand.

		args = ['voice2json', 'transcribe-stream', '--exit-count', '1']
		if open:
			args.append("--open")
		transcriber = Popen(args, stdout=PIPE, stderr=PIPE)
		procs.append(transcriber)
		logging.debug("Started transcriber with args: {}".format(args))

		if not open:
			recognizer = Popen(['voice2json', 'recognize-intent'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
			procs.append(recognizer)
			logging.debug("Started recognizer")

		# Wait until we see a line "Ready" on transcriber stderr
		for line in transcriber.stderr:
			if line.strip() == 'Ready':
				break
		else:
			raise Exception("Transcriber died without becoming ready")
		logging.debug("Transcriber is ready")
		ready.set()

		# Wait until transcriber exits, or timeout expires.
		transcription = None
		with gevent.Timeout(timeout, False):
			transcription = transcriber.stdout.read()

		if transcription is None:
			logging.debug("Transcriber timed out")
			return None

		# Check transcriber exited success, or else our transcription is bogus
		if transcriber.wait() != 0:
			raise Exception("Transcriber exited with status: {}".format(transcriber.returncode))

		logging.debug("Got event from transcriber: {}".format(transcription))

		# For open transcription, stop here and return the raw transcription
		if open:
			response = json.loads(transcription)
			return ListenResponse(
				text = response["text"],
				intent = None,
				groups = {},
			)

		# Feed the transcription through the recognizer
		response, stderr = recognizer.communicate(transcription)
		if recognizer.wait() != 0:
			raise Exception("Recognizer exited with status: {}\n{}".format(recognizer.returncode, stderr))
		logging.debug("Got event from recognizer: {}".format(response))

		# Finally, parse it into a ListenResponse
		response = json.loads(response)

		intent = None
		if response["intent"]["name"] != "" and response["intent"]["confidence"] > 0.5:
			intent = response["intent"]["name"]

		return ListenResponse(
			text = response['raw_text'],
			intent = intent,
			groups = response["slots"],
		)

	finally:
		# Kill all running procs
		for proc in procs:
			try:
				if proc.poll() is None:
					proc.kill()
			except EnvironmentError:
				pass # this means the process died between poll and kill, which is fine


def start_listening(open=False, timeout=10):
	"""Begin running listener. Return when listener is ready and listening,
	returning the listener greenlet. You can wait on that greenlet to get the response,
	or kill it to cancel listening.
	If open=True, listener will listen for arbitrary text instead of an intent.
	Listener will return either None (if timeout is exceeded without any speech),
	or a ListenResponse.
	"""
	ready = gevent.event.Event()
	listener = gevent.spawn(_run_listener, ready, open, timeout)
	gevent.wait([ready, listener], count=1) # wait for either, in case listener dies
	return listener
