
import json
import logging
from collections import namedtuple

import gevent
from gevent.subprocess import PIPE, Popen

from . import intents as _ # for side effects
from . import sounds
from .intent import run_intent
from .util import kill_on_exit, run_command


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


def wait_for_wake():
	# TODO: Instead of one-shot, have it always running but discard all pending wakes
	# each time we start waiting.
	stdout = run_command("voice2json", "wait-wake", "--exit-count", "1")
	logging.debug("Got output from wait-wake: {}".format(stdout))


def wake_and_listen():
	logging.info("Waiting for wake word")
	wait_for_wake()
	logging.info("Woken up")

	ATTEMPTS = 3
	for attempt in range(ATTEMPTS):

		# Start listening. This blocks until listening has started.
		# When we exit the block, the listener will be killed if it's still running.
		with kill_on_exit(start_listening()) as listener:

			# normally we do a "acknowledging" start-talking beep. but if this is a re-attempt
			# after an unknown intent, indicate our confusion to the user with a
			# "question" beep.
			# The flow being:
			#  1. start listening
			#  2. simple beep
			#  3. get unknown result
			#  4. start listening again
			#  5. question beep
			sounds.play(sounds.ACK if attempt == 0 else sounds.QUESTION)

			# Block until listener has detected something, failed, or timeout expires.
			response = listener.get()

		# If listener timed out without hearing anything, play an error beep so user knows
		# we've stopped, and give up.
		# We don't want to retry in this case as it probably means user didn't actually intend
		# to wake us.
		if not response:
			logging.info("No response within timeout, giving up")
			sounds.play(sounds.ERROR)
			return

		# If listener found no recognizable intent, try again.
		# Otherwise execute the intent and break, we're done.
		# Note the intent runner will ensure we indicate we ran the intent with some sound or another.
		if response.intent:
			run_intent(response)
			return

		logging.info("Unable to determine an intent from response (attempt {}/{}): {}".format(
			attempt + 1, ATTEMPTS, response,
		))

	# If we reach here, it means we got an unknown intent 3 times in a row.
	# Play an error beep and give up.
	logging.info("Ran out of attempts, giving up")
	sounds.play(sounds.ERROR)


def main():
	# The main loop is syncronous, so that we can't get confused if multiple events happen
	# at the same time. Since this is a human-interface system, this ensures clarity for the human.
	while True:
		try:
			wake_and_listen()
		except Exception:
			# Error in waking, listening, etc. Log and (try to) tell user we've failed.
			logging.exception("Error in listen loop")
			# play() might also fail, if it does there's not much we can do though.
			try:
				sounds.play(sounds.ERROR)
			except Exception:
				logging.exception("Error while trying to tell user about previous error")
