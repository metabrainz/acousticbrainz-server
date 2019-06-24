class SimilarityException(Exception):
	"""Base exception for this package."""
	pass


class IndexNotFoundException(SimilarityException):
	"""Should be used when no index of given parameters 
	has been created."""
	pass


class ItemNotFoundException(SimilarityException):
	"""Should be used when the item given item is not present
	in an index."""
	pass


class CannotAddItemException(SimilarityException):
	"""Should be used when an item is added but the index has
	already been built or saved, i.e. no more items may be added.
	"""
	pass 