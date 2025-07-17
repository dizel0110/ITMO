import pytest

from mixer.backend.django import mixer as _mixer


@pytest.fixture
def mixer():
    """The class Mixer for generate instances of different models."""
    return _mixer
