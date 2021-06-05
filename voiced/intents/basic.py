
from ..intent import intent


@intent("cancel")
def cancel(text):
	"""Do nothing and make no noise. Used as a filler response if you don't actually
	want anything to run after all."""
	return False
