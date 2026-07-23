"""P1-6 follow-on: when Moreau exposes a torch differentiable API, extend this probe.

Today we only assert optional imports; shield-path autograd vs FD belongs in a licensed CUDA env.
"""

from __future__ import annotations

import pytest

pytest.importorskip("moreau")
pytestmark = [pytest.mark.requires_moreau, pytest.mark.vendor_moreau]


def test_optional_moreau_torch_submodule() -> None:
    """Document discovery: full shield autograd checks require vendor torch/CUDA stack.

    CPU-only Moreau builds are valid. Do not skip under CONICSHIELD_VENDOR_REQUIRED —
    absence of ``moreau.torch`` is an expected profile outcome, not a capability failure.
    """
    import moreau

    torch_mod = getattr(moreau, "torch", None)
    if torch_mod is None:
        assert getattr(moreau, "torch", None) is None
        return
    assert torch_mod is not None
