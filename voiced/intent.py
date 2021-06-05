
import logging

from . import sounds


# List of (name, {group keys: values that must match}, handler)
INTENTS = []


def intent(_name, **values):
	"""Decorator that registers an intent handler.
	Intent name is required. In addition, kwargs may be given that specify group keys
	that must match the given value.
	For example, @intent("foo", kind="bar") will handle events where the intent name
	is "foo", and there is a capture group "kind" whose value equals "bar".

	Intent handlers are passed the full input text as the first arg, and any capture groups
	as kwargs. They may return a sound to play when complete, or False to play no sound.
	By default (if they return None), a sounds.ACK is played. If they raise, a sounds.ERROR
	is played.

	Handlers are matched in definition order, so a more specific match followed by a general one
	will result in only matches that don't match the first one going to the second, eg:
		@intent("foo", bar="baz")
		def foo_baz(text, bar):
			...

		@intent("foo")
		def foo_not_baz(text, bar):
			...
	In this example, foo_not_baz will only be called for intents where bar != "baz".
	However, if these were defined in the opposite order, then foo_baz would never match
	because all "foo" intents (including where bar = "baz") would be handled by foo_not_baz.
	"""
	def _intent_register(fn):
		INTENTS.append((_name, values, fn))
		return fn
	return _intent_register


def run_intent(response):
	for name, values, handler in INTENTS:
		if name == response.intent and all(
			k in response.groups and response.groups[k] == v
			for k, v in values.items()
		):
			logging.debug("Found matching handler {} for response {}".format((name, values, handler), response))
			break
	else:
		raise Exception("No intent handler matches for response: {}".format(response))

	try:
		sound = handler(response.text, **response.groups)
		logging.debug("Got handler return value: {}".format(sound))
	except Exception:
		logging.exception("Error in intent handler {} for response: {}".format(handler, response))
		sound = sounds.ERROR

	if sound is None:
		sound = sounds.ACK
	if sound:
		sounds.play(sound)
