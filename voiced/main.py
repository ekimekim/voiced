
import logging


def main():

	# The main loop is syncronous, so that we can't get confused if multiple events happen
	# at the same time. Since this is a human-interface system, this ensures clarity for the human.
	while True:
		try:
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
					play(sounds.ACK if attempt == 1 else sounds.QUESTION)

					# Block until listener has detected something, or failed (which will raise)
					response = listener.get()

				# If listener found no recognizable intent, try again.
				# Otherwise execute the intent and break, we're done.
				if response.intent:
					run_intent(intent)
					break

				logging.info("Unable to determine an intent from response (attempt {}/{}): {}".format(
					attempt + 1, ATTEMPTS, response,
				))

			else:
				# If we reach here, it means we got an unknown intent 3 times in a row.
				# Play an error beep and give up.
				logging.info("Ran out of attempts, giving up")
				play(sounds.ERROR)
		except ListenTimeout:
			# Listener gave up after not hearing anything. Play an error beep so user knows
			# we've given up.
			logging.info("No response within timeout, giving up")
			play(sounds.ERROR)
		except Exception:
			# Error in waking, listening, etc. Log and tell user we've failed.
			logging.exception("Error in wake loop")
			play(sounds.ERROR)
