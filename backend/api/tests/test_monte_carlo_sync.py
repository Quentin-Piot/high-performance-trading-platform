"""
Tests for synchronous Monte Carlo simulation endpoint.

This module tests the new synchronous Monte Carlo endpoint that executes
simulations directly without using the queue system.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.simple_auth import SimpleUser, get_current_user_simple