from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
USER_SETTINGS_PATH = ROOT / "app" / "services" / "user_settings.py"


def _load_user_settings_module():
    account_context_mod = types.ModuleType("app.services.account_context")
    current = {"value": "_default"}
    account_context_mod.get_account_id = lambda: current["value"]
    sys.modules["app.services.account_context"] = account_context_mod

    spec = importlib.util.spec_from_file_location(
        "test_account_credentials_user_settings", USER_SETTINGS_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._test_account_context = current
    return module


def test_effective_llm_keys_are_account_scoped(tmp_path):
    module = _load_user_settings_module()
    module._SETTINGS_DIR = tmp_path

    module.update_user_settings(
        account_id="acct-a",
        llm_apis=[{"providerKey": "deepseek", "key": "A1,A2"}],
    )
    module.update_user_settings(
        account_id="acct-b",
        llm_apis=[{"providerKey": "deepseek", "key": "B1"}],
    )

    module._test_account_context["value"] = "acct-a"
    keys_a = module.get_effective_llm_keys(provider_key="deepseek", env_keys=["ENV"])

    module._test_account_context["value"] = "acct-b"
    keys_b = module.get_effective_llm_keys(provider_key="deepseek", env_keys=["ENV"])

    assert keys_a == ["A1", "A2", "ENV"]
    assert keys_b == ["B1", "ENV"]


def test_effective_volcengine_credentials_are_account_scoped(tmp_path):
    module = _load_user_settings_module()
    module._SETTINGS_DIR = tmp_path

    module.update_user_settings(
        account_id="acct-a",
        volcengine={"access_key": "AK_A", "secret_key": "SK_A"},
    )
    module.update_user_settings(
        account_id="acct-b",
        volcengine={"access_key": "AK_B", "secret_key": "SK_B"},
    )

    module._test_account_context["value"] = "acct-a"
    creds_a = module.get_effective_volcengine_credentials(
        env_access_key="ENV_AK", env_secret_key="ENV_SK"
    )

    module._test_account_context["value"] = "acct-b"
    creds_b = module.get_effective_volcengine_credentials(
        env_access_key="ENV_AK", env_secret_key="ENV_SK"
    )

    assert creds_a == {"access_key": "AK_A", "secret_key": "SK_A"}
    assert creds_b == {"access_key": "AK_B", "secret_key": "SK_B"}
