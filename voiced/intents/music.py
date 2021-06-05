
import logging

from ..intent import intent


@intent("music")
def music(text, command, volume=None):
	logging.info("STUB: music intent: {}, volume={}".format(command, volume))
