
import logging

from . import intents as _ # for side effects
from . import sounds
from .intent import run_intent
from .listen import start_listening
from .util import kill_on_exit, run_command


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
