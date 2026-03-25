from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
LLM_PATH = ROOT / "app" / "llm.py"


def _load_llm_module():
    current = {"account_id": "_default"}
    account_context_mod = types.ModuleType("app.services.account_context")
    account_context_mod.get_account_id = lambda: current["account_id"]
    sys.modules["app.services.account_context"] = account_context_mod

    user_settings_mod = types.ModuleType("app.services.user_settings")
    user_settings_mod.get_effective_llm_keys = lambda provider_key, env_keys: [
        f"{current['account_id']}-1",
        f"{current['account_id']}-2",
    ]
    user_settings_mod.get_agent_llm_overrides = lambda: {}
    user_settings_mod.get_agent_api_config = lambda agent_name: None
    sys.modules["app.services.user_settings"] = user_settings_mod

    config_mod = types.ModuleType("app.config")
    config_mod.settings = types.SimpleNamespace(
        GEMINI_API_KEYS=[],
        MOONSHOT_API_KEYS=[],
        OPENAI_API_KEY="",
        DEEPSEEK_API_KEYS=[],
        DEEPSEEK_BASE_URL="https://api.deepseek.com",
        DOUBAO_API_KEYS=[],
        DOUBAO_BASE_URL="https://ark.cn-beijing.volces.com/api/v3",
        ZHIPU_API_KEYS=[],
        ZHIPU_BASE_URL="https://open.bigmodel.cn/api/paas/v4",
        AGENT_CONFIG={"writer": [{"provider": "deepseek", "model": "deepseek-chat"}]},
        DEEPSEEK_MODEL="deepseek-chat",
    )
    sys.modules["app.config"] = config_mod

    sys.modules["langchain_google_genai"] = types.ModuleType("langchain_google_genai")
    sys.modules["langchain_google_genai"].ChatGoogleGenerativeAI = object
    sys.modules["langchain_openai"] = types.ModuleType("langchain_openai")
    sys.modules["langchain_openai"].ChatOpenAI = lambda **kwargs: kwargs

    spec = importlib.util.spec_from_file_location(
        "test_llm_module_shared_cache", LLM_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._test_account_context = current
    return module


def test_key_rotation_state_is_partitioned_by_account():
    module = _load_llm_module()

    module._test_account_context["account_id"] = "acct-a"
    manager_a = module._get_manager("deepseek", ["acct-a-1", "acct-a-2"], "DeepSeek")
    module._test_account_context["account_id"] = "acct-b"
    manager_b = module._get_manager("deepseek", ["acct-b-1", "acct-b-2"], "DeepSeek")

    assert manager_a.get_next_key() == "acct-a-1"
    assert manager_a.get_next_key() == "acct-a-2"
    assert manager_b.get_next_key() == "acct-b-1"
    assert manager_b.get_next_key() == "acct-b-2"
